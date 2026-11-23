"""The quote draft: what the model proposes from one normalized document.

This is the "Canonical JSON" of the ingestion pipeline (docs/05-ingestion-pipeline.md,
stage 4). It's a proposal, so it stays deliberately forgiving:

- It checks types and shape only. Business rules, such as a quantity above zero
  or a known vendor, belong to the validation stage, where a failure becomes a
  review issue. Rejecting a draft here would lose it instead.
- Nearly every field is optional, because any given quote may not state it.
- Component types with a spec file in docs/03-component-library/ get their own
  shape holding only the properties that file lists (so far: CPU, memory, GPU, storage, network
  adapters, DPUs, power supplies, RAID controllers, and the chassis on the item). The other
  types share a generic shape until their spec files are written.
- It holds no catalog IDs, match states, confidence scores or provenance. Later
  stages and the dispatch layer add those, and the model should never invent them.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Generic, Literal, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema

# Pydantic's default Decimal schema includes a regex with a lookahead, which
# llama.cpp's grammar converter can't handle. The model emits a plain number and
# Pydantic still converts it to an exact Decimal.
Money = Annotated[Decimal, WithJsonSchema({"type": "number"})]


class ComponentType(str, Enum):
    # Hardware, from docs/03-component-library/ and docs/04-system-library.md.
    CHASSIS = "chassis"
    MOTHERBOARD = "motherboard"
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    GPU = "gpu"
    ACCELERATOR = "accelerator"
    NIC = "nic"
    DPU = "dpu"
    PSU = "psu"
    RAID_CONTROLLER = "raid_controller"  # HBAs and tri-mode cards too (08-raid-controller.md)
    TPM = "tpm"
    FAN = "fan"
    CABLE = "cable"
    RAIL_KIT = "rail_kit"
    # Commercial lines. These appear on quotes but aren't installed hardware, so
    # they must stay out of a configuration's fingerprint.
    LICENSE = "license"
    WARRANTY = "warranty"
    SUPPORT = "support"
    SERVICE = "service"
    OTHER = "other"


class QuantityBasis(str, Enum):
    """What a component's stated quantity counts.

    Vendors differ: "2x CPU" under a line of 8 servers means 2 per server, while
    "(x8) CPU" under a line of 4 servers can mean 8 across the whole order.
    """

    PER_UNIT = "per_unit"
    ORDER_TOTAL = "order_total"
    UNKNOWN = "unknown"


class _Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Basis(str, Enum):
    """Where a property's value came from (docs/03-component-library/00-overview.md, section 4)."""

    STATED = "stated"
    INFERRED = "inferred"


T = TypeVar("T")


class Property(_Draft, Generic[T]):
    """One property value, marked as stated in the quote or inferred by the model.

    Inferred values are flagged in review and offered unselected, so they never
    become catalog information without approval.
    """

    value: T
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class CpuProperties(_Draft):
    """The CPU's identity and specifications: the reusable library record.

    Only the properties docs/03-component-library/01-cpu.md lists, in its units.
    """

    manufacturer: Property[str] | None = None
    product_family: Property[str] | None = Field(default=None, description="Such as EPYC or Xeon, without a tier.")
    model: Property[str] | None = Field(
        default=None,
        description="The manufacturer's model designation, such as 9654, including any tier, such as Gold 6438N.",
    )
    code_name: Property[str] | None = None
    physical_cores: Property[int] | None = None
    threads: Property[int] | None = None
    base_clock_ghz: Property[float] | None = None
    cache_mb: Property[float] | None = Field(default=None, description="Total L3 cache, in MB.")
    tdp_w: Property[float] | None = None


class CpuComponent(_Draft):
    """A CPU line of a configuration."""

    component_type: Literal["cpu"]
    cpu: CpuProperties = Field(default_factory=CpuProperties)
    # The quantity as written, and what it counts. Read to work out the CPUs
    # installed per server (8 across 4 servers is 2), which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices CPUs separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one CPU model could match, or the document contradicts itself.",
    )


class ModuleHeight(_Draft):
    """Module height exactly as the quote writes it, with its meaning kept separately (02-memory.md, rule 7)."""

    value: str = Field(description="As written in the quote, such as LP.")
    meaning: str | None = Field(default=None, description="What it means, if known, such as Low Profile.")
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class MemoryProperties(_Draft):
    """The memory module's identity and specifications: the reusable library record.

    Only the properties docs/03-component-library/02-memory.md lists, in its order and units.
    """

    manufacturer: Property[str] | None = None
    product_family: Property[str] | None = Field(default=None, description="Such as DDR5 Server Memory, if identifiable.")
    model: Property[str] | None = Field(default=None, description="The manufacturer's model designation.")
    mpn: Property[str] | None = Field(
        default=None,
        description="The manufacturer's own part or ordering code, never the vendor's.",
    )
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    memory_type: Property[str] | None = Field(default=None, description="The memory technology, such as DDR4 or DDR5.")
    form_factor: Property[str] | None = Field(default=None, description="Such as RDIMM, LRDIMM, UDIMM or SODIMM.")
    capacity_gb: Property[int] | None = Field(default=None, description="Capacity of one module, in GB.")
    data_rate_mts: Property[int] | None = Field(default=None, description="Effective data rate in MT/s, such as 6400.")
    operating_frequency_mhz: Property[int] | None = Field(
        default=None,
        description="Clock frequency in MHz, only if the quote states it as such. Never the data rate.",
    )
    ecc: Property[bool] | None = None
    rank: Property[int] | None = None
    dram_organization: Property[Literal["x4", "x8", "x16"]] | None = None
    dram_density_gb: Property[int] | None = Field(default=None, description="Density of one DRAM chip, in Gb.")
    module_height: ModuleHeight | None = None
    voltage_v: Property[float] | None = None
    cas_latency: Property[int] | None = Field(default=None, description="In clock cycles.")


class MemoryComponent(_Draft):
    """A memory line of a configuration."""

    component_type: Literal["memory"]
    memory: MemoryProperties = Field(default_factory=MemoryProperties)
    # As for CPUs: read to work out the modules installed per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices modules separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one module could match, only a total is given, or the document contradicts itself.",
    )


class Measured(_Draft, Generic[T]):
    """A number in the spec's unit, keeping the quote's wording when it was converted (04-gpu.md, rule 16)."""

    value: T
    as_written: str | None = Field(
        default=None,
        description="The quote's own wording, such as 1.6 TB/s, when the value was converted to another unit.",
    )
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class CoreCount(_Draft):
    """Processing cores in the manufacturer's own terms, which differ in meaning (04-gpu.md, rule 6)."""

    value: int
    terminology: str = Field(description="The manufacturer's term, such as CUDA cores or Stream processors.")
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class GpuPower(_Draft):
    """GPU power, saying which figure it is (04-gpu.md, rule 9)."""

    value: float
    kind: Literal["max_board_power", "power_limit", "typical"] | None = Field(
        default=None,
        description="Which figure this is. Null if the quote doesn't make it clear.",
    )
    as_written: str | None = None
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class GpuProperties(_Draft):
    """The GPU's identity and specifications: the reusable library record.

    The properties docs/03-component-library/04-gpu.md lists, in its order and
    units. The card maker is kept apart from the GPU maker (rule 3), and the
    vendor's own code is kept as well.
    """

    manufacturer: Property[str] | None = Field(default=None, description="The GPU chip's manufacturer, such as NVIDIA.")
    board_manufacturer: Property[str] | None = Field(
        default=None,
        description="The card's manufacturer, such as an OEM for an OEM-branded card.",
    )
    product_family: Property[str] | None = None
    model: Property[str] | None = Field(default=None, description="The manufacturer's model designation, as quoted.")
    mpn: Property[str] | None = Field(
        default=None,
        description="The card manufacturer's own part number, never the vendor's.",
    )
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    architecture: Property[str] | None = None
    gpu_chip: Property[str] | None = Field(default=None, description="Such as GH100.")
    memory_capacity_gb: Measured[int] | None = Field(default=None, description="Onboard memory of one GPU, in GB.")
    memory_type: Property[str] | None = None
    memory_bandwidth_gbs: Measured[float] | None = Field(default=None, description="In GB/s.")
    memory_interface_bits: Property[int] | None = None
    processing_cores: CoreCount | None = None
    tensor_cores: Property[int] | None = None
    base_clock_mhz: Measured[float] | None = None
    boost_clock_mhz: Measured[float] | None = None
    interface: Property[str] | None = Field(default=None, description="Such as PCIe 5.0 x16 or SXM5.")
    form_factor: Property[str] | None = Field(default=None, description="Such as PCIe add-in card or SXM.")
    cooling: Property[str] | None = Field(default=None, description="Such as Passive or Active.")
    power_w: GpuPower | None = None
    power_connector: Property[str] | None = None
    nvlink_support: Property[bool] | None = None
    nvlink_bandwidth_gbs: Measured[float] | None = None


class GpuComponent(_Draft):
    """A GPU line of a configuration."""

    component_type: Literal["gpu"]
    gpu: GpuProperties = Field(default_factory=GpuProperties)
    # As for CPUs: read to work out the GPUs installed per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices GPUs separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one GPU could match, a value depends on the card variant, "
        "or the document contradicts itself.",
    )


class Capacity(_Draft):
    """A drive's capacity with its unit as written (03-storage.md, rules 18-19)."""

    value: float
    unit: Literal["GB", "TB"]
    as_written: str | None = Field(
        default=None,
        description="The quote's own wording, when a rule changed the value, such as 3.8TB.",
    )
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class Endurance(_Draft):
    """Endurance in the manufacturer's own metric, never converted (03-storage.md, rule 10)."""

    value: float
    metric: str = Field(description="Such as DWPD or TBW.")
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class StoragePower(_Draft):
    """One power figure, labeled with what it is (03-storage.md, rule 8)."""

    value: float
    kind: Literal["maximum", "typical", "average"] | None = Field(
        default=None,
        description="Which figure this is. Null if the quote doesn't make it clear.",
    )
    basis: Basis
    reason: str | None = Field(default=None, description="For an inferred value: what it was worked out from.")


class StorageProperties(_Draft):
    """The drive's identity and specifications: the reusable library record.

    Only the properties docs/03-component-library/03-storage.md lists, in its order and units.
    """

    manufacturer: Property[str] | None = None
    product_family: Property[str] | None = Field(default=None, description="Such as PM9A3.")
    model: Property[str] | None = Field(default=None, description="The manufacturer's drive model designation.")
    mpn: Property[str] | None = Field(
        default=None,
        description="The manufacturer's own part or ordering code, never the vendor's.",
    )
    storage_type: Property[str] | None = Field(default=None, description="SSD or HDD.")
    form_factor: Property[str] | None = Field(default=None, description="Such as 2.5-inch, 3.5-inch, M.2 2280 or E1.S.")
    connector: Property[str] | None = Field(default=None, description="Such as U.2, U.3, M.2 or SATA.")
    interface: Property[str] | None = Field(default=None, description="Such as NVMe PCIe 4.0 x4 or SAS 12 Gb/s.")
    capacity: Capacity | None = Field(default=None, description="Of one drive.")
    flash_technology: Property[str] | None = Field(default=None, description="Such as TLC, QLC, CMR or SMR.")
    endurance: Endurance | None = None
    power_w: StoragePower | None = None
    encryption: Property[str] | None = Field(default=None, description="Such as SED, TCG Opal 2.0 or Non-SED.")


class StorageComponent(_Draft):
    """A storage line of a configuration: one group of identical drives."""

    component_type: Literal["storage"]
    storage: StorageProperties = Field(default_factory=StorageProperties)
    # As for CPUs: read to work out the drives in this group per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices drives separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one drive could match, a part number may be shortened, a value depends on the "
        "variant, or the document contradicts itself.",
    )


class NicProperties(_Draft):
    """The network adapter's identity and specifications: the reusable library record.

    The properties docs/03-component-library/05-network-adapter.md lists, in its
    order, with the changes approved on 2026-11-16 (Vendor Product ID and Crypto
    added, maximum power dropped). DPUs (their own type) and onboard ports aren't adapters (rules 21-22).
    """

    manufacturer: Property[str] | None = Field(default=None, description="Such as NVIDIA, Intel or Broadcom.")
    product_family: Property[str] | None = Field(default=None, description="Such as ConnectX-7 or Ethernet 800 Series.")
    model: Property[str] | None = Field(
        default=None, description="The specific model or variant, more specific than the family, such as E810-XXVDA2."
    )
    mpn: Property[str] | None = Field(default=None, description="The manufacturer's ordering code, never the vendor's.")
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    adapter_type: Property[str] | None = Field(
        default=None, description="The category: NIC, SmartNIC, HCA (Host Channel Adapter) or CNA."
    )
    network_technology: Property[str] | None = Field(
        default=None, description="Ethernet and InfiniBand for an IB/EN or VPI card; otherwise such as Ethernet or InfiniBand."
    )
    port_count: Property[int] | None = Field(default=None, description="Physical network ports.")
    port_speed_gbps: Measured[float] | None = Field(
        default=None,
        description="The maximum speed of one port, in Gb/s. When several speeds are listed, such as 10/25GbE, "
        "the highest, with the quote's wording in as_written. Never the total across ports.",
    )
    port_connector: Property[str] | None = Field(default=None, description="Such as SFP28, QSFP28, QSFP-DD, OSFP or RJ45.")
    host_interface: Property[str] | None = Field(
        default=None, description="The connection to the server, such as PCIe 5.0 x16. Never OCP 3.0, which is a form factor."
    )
    form_factor: Property[str] | None = Field(
        default=None, description="Such as PCIe full-height, PCIe low-profile or OCP 3.0 SFF."
    )
    rdma_support: Property[str] | None = Field(default=None, description="The RDMA protocol, such as RoCEv2 or InfiniBand.")
    crypto: Property[str] | None = Field(
        default=None, description="The crypto variant exactly as written, such as NoCrypto. Never inferred."
    )


class NicComponent(_Draft):
    """A network adapter line of a configuration."""

    component_type: Literal["nic"]
    nic: NicProperties = Field(default_factory=NicProperties)
    # As for CPUs: read to work out the adapters installed per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices adapters separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one adapter could match, a value depends on the variant, "
        "or the document contradicts itself.",
    )


class DpuProperties(_Draft):
    """The DPU's identity and specifications: the reusable library record.

    The properties docs/03-component-library/09-dpu.md lists, in its order, with
    Vendor Product ID (rule 3) and the crypto variant, as for network adapters,
    added (approved 2026-11-23). A DPU's own network ports are part of it, never a
    separate network adapter (section 5).
    """

    manufacturer: Property[str] | None = Field(default=None, description="Such as NVIDIA or AMD.")
    product_family: Property[str] | None = Field(default=None, description="Such as BlueField or Pensando.")
    model: Property[str] | None = Field(
        default=None, description="The commercial model, with its generation and variant, such as BlueField-2 MBF2M516A."
    )
    mpn: Property[str] | None = Field(default=None, description="The manufacturer's part number, never the vendor's code.")
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    processor_architecture: Property[str] | None = Field(
        default=None,
        description="The DPU's own cores, such as Arm Cortex-A78, never the host's CPU. Only as written, never inferred.",
    )
    cpu_cores: Property[int] | None = Field(
        default=None,
        description="The DPU's general-purpose cores, never host cores or accelerator engines. Only as written, never inferred.",
    )
    network_technology: Property[str] | None = Field(
        default=None, description="Ethernet and InfiniBand for an IB/EN or VPI card; otherwise such as Ethernet or InfiniBand."
    )
    port_count: Property[int] | None = Field(default=None, description="Physical network ports.")
    port_speed_gbps: Measured[float] | None = Field(
        default=None,
        description="The maximum speed of one port, in Gb/s, never the total across ports, with the quote's wording "
        "in as_written when it's converted or several speeds are listed.",
    )
    port_connector: Property[str] | None = Field(default=None, description="Such as QSFP112, QSFP56 or SFP56.")
    host_interface: Property[str] | None = Field(
        default=None, description="The connection to the server, such as PCIe 5.0 x16, never the network ports."
    )
    onboard_memory_gb: Measured[float] | None = Field(
        default=None,
        description="The DPU's own memory in GB, never host or GPU memory, with the type, such as DDR5, in as_written. "
        "Only as written, never inferred.",
    )
    hardware_acceleration: Property[str] | None = Field(
        default=None,
        description="The hardware engines in the manufacturer's terms, such as packet processing, compression. "
        "Only as written, never inferred.",
    )
    storage_connectivity: Property[str] | None = Field(
        default=None, description="Such as NVMe, NVMe-oF. Only as written, never inferred."
    )
    form_factor: Property[str] | None = Field(
        default=None, description="Such as PCIe full-height, PCIe low-profile or OCP 3.0. Never from the host interface alone."
    )
    crypto: Property[str] | None = Field(
        default=None, description="The crypto variant exactly as written, such as Crypto Enable or NoCrypto. Never inferred."
    )


class DpuComponent(_Draft):
    """A DPU line of a configuration."""

    component_type: Literal["dpu"]
    dpu: DpuProperties = Field(default_factory=DpuProperties)
    # As for CPUs: read to work out the DPUs installed per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices DPUs separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one DPU could match, a value depends on the variant, or the document contradicts itself.",
    )


class PsuProperties(_Draft):
    """The power supply's identity and specifications: the reusable library record.

    The properties docs/03-component-library/06-power-supply.md lists, in its
    order, with Vendor Product ID added (approved 2026-11-19). Quantity belongs to
    the quote occurrence; redundancy and total installed capacity belong to the
    System Library configuration (section 6), so neither is a property here.
    """

    manufacturer: Property[str] | None = Field(
        default=None, description="The power supply's own maker, such as Delta or Lite-On. Never the server's brand."
    )
    product_family: Property[str] | None = Field(default=None, description="The manufacturer's series, such as Titanium PSU series.")
    model: Property[str] | None = Field(default=None, description="The manufacturer's model designation, such as PWS-1K28P-SQ.")
    mpn: Property[str] | None = Field(default=None, description="The manufacturer's part number, never the vendor's code.")
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    rated_output_w: Measured[int] | None = Field(
        default=None,
        description="One power supply's rated output in W, never the total across power supplies. With "
        "ratings that depend on the input voltage, the highest, with the quote's wording in as_written.",
    )
    power_supply_type: Property[str] | None = Field(default=None, description="AC or DC input.")
    ac_input_phase: Property[str] | None = Field(
        default=None, description="Such as Single-phase, 3-phase, Wye (Y) or Delta. Only as written, never inferred."
    )
    input_voltage: Property[str] | None = Field(default=None, description="The supported range, such as 100-240 V AC or 48 V DC.")
    input_frequency: Property[str] | None = Field(default=None, description="Such as 50/60 Hz. Empty for a DC-only power supply.")
    input_connector: Property[str] | None = Field(
        default=None,
        description="The power supply's inlet, such as IEC C14, IEC C20 or terminal block; never the cord. "
        "Only as written, never inferred.",
    )
    efficiency_certification: Property[str] | None = Field(
        default=None, description="Exactly as written, such as Titanium or 80 PLUS Platinum. Never from a percentage."
    )
    form_factor: Property[str] | None = Field(default=None, description="Such as CRPS, Flex ATX or Flex Slot.")
    hot_swap: Property[bool] | None = Field(
        default=None, description="True when written hot-plug or hot-swap; null when unknown."
    )


class PsuComponent(_Draft):
    """A power supply line of a configuration."""

    component_type: Literal["psu"]
    psu: PsuProperties = Field(default_factory=PsuProperties)
    # As for CPUs: read to work out the power supplies installed per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices power supplies separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"redundant\" or \"1+1\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one power supply could match, the rating depends on the input voltage, "
        "or the document contradicts itself.",
    )


class RaidControllerProperties(_Draft):
    """The storage controller's identity and specifications: the reusable library record.

    The properties docs/03-component-library/08-raid-controller.md lists, in its
    order, with Vendor Product ID added as for the other parts (2026-11-23). It
    covers hardware RAID controllers, HBAs and tri-mode cards; RAID built into the
    motherboard isn't a controller (section 1). What it can do, never how it's set
    up: arrays, connected drives and the RAID level in use belong to the System
    Library configuration (section 6).
    """

    manufacturer: Property[str] | None = Field(default=None, description="Such as Broadcom or Microchip.")
    product_family: Property[str] | None = Field(default=None, description="The manufacturer's series, such as MegaRAID.")
    model: Property[str] | None = Field(default=None, description="The commercial model designation, such as MegaRAID 9560-16i.")
    mpn: Property[str] | None = Field(default=None, description="The manufacturer's part number, never the vendor's code.")
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    controller_type: Property[str] | None = Field(
        default=None,
        description="Hardware RAID, HBA or Tri-Mode. An HBA isn't a RAID controller just because it connects drives.",
    )
    host_interface: Property[str] | None = Field(
        default=None, description="The connection to the server, never the drives, such as PCIe 4.0 x8."
    )
    external_ports: Property[str] | None = Field(
        default=None, description="Count and connector, such as 4 x SFF-8644. Only as written, never inferred."
    )
    internal_ports: Property[str] | None = Field(
        default=None, description="Count and connector, such as 2 x SFF-8654 x8. Only as written, never inferred."
    )
    supported_drive_interfaces: Property[str] | None = Field(
        default=None, description="Such as SAS, SATA, NVMe. Only as written, never from the connector."
    )
    max_drive_count: Property[int] | None = Field(
        default=None,
        description="The maximum the manufacturer supports, never the drives in the server. Only as written, never inferred.",
    )
    raid_levels: Property[str] | None = Field(
        default=None, description="Exactly the supported levels, such as RAID 0, 1, 5, 6, 10. Only as written, never inferred."
    )
    cache_capacity_gb: Measured[float] | None = Field(
        default=None,
        description="The controller's own cache, in GB, never system memory. Only as written, never inferred.",
    )
    cache_protection: Property[str] | None = Field(
        default=None,
        description="Such as CacheVault, flash-backed or battery-backed. Never for ordinary cache. Only as written, never inferred.",
    )
    boot_support: Property[bool] | None = Field(
        default=None, description="True only when written that it can boot from its drives. Only as written, never inferred."
    )


class RaidControllerComponent(_Draft):
    """A RAID controller, HBA or tri-mode controller line of a configuration."""

    component_type: Literal["raid_controller"]
    raid_controller: RaidControllerProperties = Field(default_factory=RaidControllerProperties)
    # As for CPUs: read to work out the controllers installed per server, which is what's stored.
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices controllers separately.")
    note: str | None = Field(
        default=None,
        description="Context the quote gives about this part that no property holds, as written, such as "
        "\"BOSS boot\". Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="More than one controller could match, the type isn't clear, or the document contradicts itself.",
    )


class ChassisProperties(_Draft):
    """The chassis properties from docs/03-component-library/07-chassis.md, section 2.

    What the enclosure supports, never what's installed in it: the drives, power
    supplies and fans fitted belong to the System Library configuration.
    """

    manufacturer: Property[str] | None = Field(
        default=None, description="The enclosure's own maker, such as Supermicro. Never assumed from the vendor."
    )
    product_family: Property[str] | None = Field(default=None, description="Such as SuperServer, PowerEdge or ProLiant.")
    model: Property[str] | None = Field(
        default=None,
        description="The chassis's own designation, such as CSE-829U. The server's or base system's model only "
        "when no chassis model is given, with a review flag.",
    )
    mpn: Property[str] | None = Field(default=None, description="The manufacturer's part number, never the vendor's code.")
    vendor_product_id: Property[str] | None = Field(default=None, description="The vendor's own product code or SKU.")
    chassis_type: Property[str] | None = Field(
        default=None, description="Such as Rackmount, Tower, Blade or Modular enclosure. Not the rack height."
    )
    form_factor: Property[str] | None = Field(
        default=None, description="The mounting standard, such as 19-inch rackmount. Never the motherboard's form factor."
    )
    rack_height: Property[str] | None = Field(default=None, description="In rack units, such as 2U.")
    dimensions: Measured[str] | None = Field(
        default=None,
        description="External dimensions in mm, with the source's labels, such as W 437 x H 89 x D 647 mm. "
        "Only as written, never inferred.",
    )
    drive_bays: Property[str] | None = Field(
        default=None,
        description="The bays the chassis has, not the drives installed, such as 12 x 3.5-inch front hot-swap. "
        "Only as written, never inferred.",
    )
    expansion_slots: Property[str] | None = Field(
        default=None, description="Such as 4 x PCIe 5.0 x16 FHFL. Only as written, never inferred."
    )
    psu_bays: Property[str] | None = Field(
        default=None,
        description="The power supply positions, not the power supplies installed, such as 2 x CRPS. "
        "Only as written, never inferred.",
    )
    cooling: Property[str] | None = Field(
        default=None, description="Such as 6 x 80 mm hot-swap fans or front-to-rear airflow. Only as written, never inferred."
    )


class ItemChassis(ChassisProperties):
    """A quote item's chassis: the enclosure of the server the item quotes.

    It sits on the item, not among its components. The item's line is the server
    or base system, and the model made a component from that same line and then
    began a new item at the next priced row (2026-11-19). One chassis per item, so
    its quantity and price are the item's.
    """

    note: str | None = Field(
        default=None,
        description="Context the quote gives about the chassis that no property holds, as written. Never a specification.",
    )
    review_flags: list[str] = Field(
        default_factory=list,
        description="The model is the server's rather than the chassis's own, more than one chassis could match, "
        "or the document contradicts itself.",
    )


# The types that have their own shape. The generic shape leaves them out of the
# JSON schema's choices, so the model can't call a line a CPU and then skip the
# CPU properties.
SPECIFIED_TYPES = {
    ComponentType.CPU,
    ComponentType.MEMORY,
    ComponentType.GPU,
    ComponentType.STORAGE,
    ComponentType.NIC,
    ComponentType.DPU,
    ComponentType.PSU,
    ComponentType.RAID_CONTROLLER,
    ComponentType.CHASSIS,  # on the quote item, not among its components
}
GenericComponentType = Literal[tuple(t.value for t in ComponentType if t not in SPECIFIED_TYPES)]


class GenericComponent(_Draft):
    """A line of a type that has no spec file yet: a part, or a service sold with it."""

    component_type: GenericComponentType  # type: ignore[valid-type]
    raw_text: str = Field(description="The vendor's original text for this line, unchanged.")
    part_number: str | None = Field(default=None, description="The vendor's part or option code.")
    manufacturer_part_number: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    quantity: int | None = None
    quantity_basis: QuantityBasis = QuantityBasis.UNKNOWN
    unit_price: Money | None = Field(default=None, description="Only if the vendor prices this line separately.")
    extended_price: Money | None = None
    specs: dict[str, str] = Field(
        default_factory=dict,
        description="Specifications stated in the text, such as capacity. Never inferred.",
    )


Component = Union[
    CpuComponent,
    MemoryComponent,
    GpuComponent,
    StorageComponent,
    NicComponent,
    DpuComponent,
    PsuComponent,
    RaidControllerComponent,
    GenericComponent,
]


class QuoteItem(_Draft):
    """One priced line of a quote, usually a server and everything in it."""

    description: str = Field(description="The vendor's original text for this item, unchanged.")
    part_number: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    quantity: int | None = None
    unit_price: Money | None = None
    # Read only to check the line's prices, or to work out a missing unit price.
    # It isn't stored: the database has quantity and unit price.
    extended_price: Money | None = None
    # Before the components, so the model fills it from the item's own line first.
    chassis: ItemChassis | None = Field(default=None, description="The server's chassis or base system. Null if the item isn't a server.")
    components: list[Component] = Field(default_factory=list)


class QuoteDraft(_Draft):
    """One quote. A single document can hold several."""

    quote_number: str | None = None
    revision: str | None = None
    vendor_name: str | None = Field(default=None, description="The company that issued the quote.")
    currency: str | None = Field(default=None, description="ISO 4217 code, such as USD.")
    quote_date: date | None = None
    subtotal: Money | None = None
    discount: Money | None = None
    tax: Money | None = None
    total: Money | None = None
    # Before the items: the model writes fields in this order, and flags written
    # after a quote's items led it to end the output there, dropping later quotes.
    review_flags: list[str] = Field(
        default_factory=list,
        description="Something about the quote as a whole the reviewer should check, such as a date taken from "
        "an email header.",
    )
    items: list[QuoteItem] = Field(default_factory=list)


class ExtractionResult(_Draft):
    """Everything extracted from one normalized document."""

    quotes: list[QuoteDraft]


def extraction_json_schema() -> dict[str, Any]:
    """The JSON schema to send to the model endpoint for constrained decoding.

    Every property is made required (it can still be null). With optional
    properties, the grammar lets the model close an object straight away, and on
    the real model it did, returning "cpu": {}. The Pydantic models themselves
    stay forgiving, so a partial draft still validates.

    Once required, the model opens every property as an object, so "value" may be
    null too. When it couldn't be, the model filled it anyway, with "Unknown", 0 or
    a "typical" guess. drop_empty_properties() turns those back into null.
    """
    schema = ExtractionResult.model_json_schema()
    _offer_only_specified_types(schema)
    for definition in [schema, *schema.get("$defs", {}).values()]:
        if "properties" in definition:
            definition["required"] = list(definition["properties"])
            if _is_property_object(definition["properties"]):
                value = definition["properties"]["value"]
                definition["properties"]["value"] = {"anyOf": [value, {"type": "null"}]}
    return schema


def _offer_only_specified_types(schema: dict[str, Any]) -> None:
    """Leave the generic shape out: only types with a reviewed spec file are extracted.

    Network cards, power supplies, services and the rest have no spec file yet,
    and the generic shape's free-form "specs" let the model run away, inventing
    "other_other_..._notes": "None" until the token limit (2026-11-13).
    """
    generic = "#/$defs/GenericComponent"
    choices = schema["$defs"]["QuoteItem"]["properties"]["components"]["items"]["anyOf"]
    choices[:] = [choice for choice in choices if choice.get("$ref") != generic]
    del schema["$defs"]["GenericComponent"]


def drop_empty_properties(data: Any) -> Any:
    """Model output with each property whose value is null replaced by null."""
    if isinstance(data, list):
        return [drop_empty_properties(item) for item in data]
    if isinstance(data, dict):
        if _is_property_object(data) and data["value"] is None:
            return None
        return {key: drop_empty_properties(value) for key, value in data.items()}
    return data


def _is_property_object(fields: dict) -> bool:
    return {"value", "basis"} <= fields.keys()
