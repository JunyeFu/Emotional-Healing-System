"""Protocol inferred by zHElEARN/brt-reverse; not a manufacturer specification.

Keep ADC integers. Neither the ECG conversion nor ACC/RRI physical units have
been verified for the user's hardware. Unknown bytes remain recordable.
"""
from dataclasses import dataclass, field
import struct

NOTIFY_UUID = "F000EFE3-0451-4000-0000-00000000B000"
WRITE_UUID = "F000EFE1-0451-4000-0000-00000000B000"
MODES = {"sport": (0, 0, 0), "ecg": (1, 0, 1), "hrv": (0, 1, 1)}


@dataclass(frozen=True)
class Packet:
    kind: str
    samples: tuple = ()
    metadata: dict = field(default_factory=dict)


def command(group, subcommand, *payload):
    return bytes([0xFC, group, subcommand, *payload]).ljust(20, b"\0")


def date_command(now):
    parts = [now.year % 100, now.month, now.day, now.hour, now.minute, now.second,
             now.isoweekday() % 7]
    bcd = [(n // 10) * 16 + n % 10 for n in parts]
    return bytes([0xFC, 0, *bcd, 0x55]).ljust(20, b"\0")


def decode_packet(raw: bytes) -> Packet:
    if len(raw) != 20:
        return Packet("unparsed", metadata={"reason": "UNEXPECTED_LENGTH"})
    group, sub = raw[:2]
    if group == 0x41:
        return Packet("ecg", struct.unpack(">9h", raw[2:]),
                      {"id": sub >> 4, "uid": sub & 15, "units": "adc_counts_unverified"})
    if (group, sub) == (0x0F, 0x12):
        values = struct.unpack(">6h", raw[4:16])
        return Packet("acc", (values[:3], values[3:]), {"units": "adc_counts_unverified"})
    if (group, sub) == (0x14, 7):
        count = raw[3]
        if count > 8:
            return Packet("unparsed", metadata={"reason": "RRI_COUNT_EXCEEDS_PACKET"})
        return Packet("rr", struct.unpack(f">{count}h", raw[4:4 + count * 2]),
                      {"device_seq": raw[2], "units": "ticks_unverified"})
    if (group, sub) == (0x14, 6):
        return Packet("hr", (struct.unpack(">h", raw[4:6])[0] / 100,),
                      {"device_seq": raw[2], "units": "bpm_protocol_unverified"})
    if group == 0x0F and sub in (0x60, 0x61, 0x62):
        name = {0x60: "ecg", 0x61: "xo", 0x62: "sr"}[sub]
        return Packet("config", metadata={name: raw[3]})
    if (group, sub) == (0x42, 0x0B):
        return Packet("config", metadata={"ecg_sr_reported": struct.unpack(">h", raw[2:4])[0]})
    return Packet("unparsed", metadata={"reason": "UNKNOWN_COMMAND"})
