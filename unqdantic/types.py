from enum import IntEnum


class UnqliteOpenFlag(IntEnum):
    READONLY = 0x00000001
    READWRITE = 0x00000002
    CREATE = 0x00000004
    EXCLUSIVE = 0x00000008
    TEMP_DB = 0x00000010
    NOMUTEX = 0x00000020
    OMIT_JOURNALING = 0x00000040
    IN_MEMORY = 0x00000080
    MMAP = 0x00000100