# Detects the system and includes the system-specific makefile.

UNAME := $(shell uname)

SYSTEM= UNKNOWN
SYSTEM_MAKEFILE= default.make
ifeq ($(UNAME),Darwin)
  SYSTEM= MACOSX
  SYSTEM_MAKEFILE= macosx.make
else ifeq ($(UNAME),Linux)
  ifeq ($(NERSC_HOST),cori)
    SYSTEM= CORI
    SYSTEM_MAKEFILE= cori.make
  endif
  ifeq ($(HOSTNAME),cheyenne1)
    SYSTEM= CHEYENNE
    SYSTEM_MAKEFILE= cheyenne.make
  endif
  ifeq ($(HOSTNAME),cheyenne2)
    SYSTEM= CHEYENNE
    SYSTEM_MAKEFILE= cheyenne.make
  endif
  ifeq ($(HOSTNAME),cheyenne3)
    SYSTEM= CHEYENNE
    SYSTEM_MAKEFILE= cheyenne.make
  endif
  ifeq ($(HOSTNAME),cheyenne4)
    SYSTEM= CHEYENNE
    SYSTEM_MAKEFILE= cheyenne.make
  endif
  ifeq ($(HOSTNAME),cheyenne5)
    SYSTEM= CHEYENNE
    SYSTEM_MAKEFILE= cheyenne.make
  endif
  ifeq ($(HOSTNAME),cheyenne6)
    SYSTEM= CHEYENNE
    SYSTEM_MAKEFILE= cheyenne.make
  endif
  ifeq ($(SYSTEM),)
    SYSTEM= LINUX
    SYSTEM_MAKEFILE= linux.make
  endif   
endif

include $(CMECDRIVERDIR)/mk/system/$(SYSTEM_MAKEFILE)

# Build identifier
BUILDID:= $(SYSTEM)

ifeq ($(OPT),TRUE)
  BUILDID:=$(BUILDID).OPT
endif

ifeq ($(DEBUG),TRUE)
  BUILDID:=$(BUILDID).DEBUG
endif

ifeq ($(PARALLEL),MPIOMP)
  BUILDID:=$(BUILDID).MPIOMP
else ifeq ($(PARALLEL),HPX)
  BUILDID:=$(BUILDID).HPX
endif

# DO NOT DELETE
