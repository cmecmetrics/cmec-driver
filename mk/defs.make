# Set compiler flags and preprocessor defines.

###############################################################################
# Configuration-independent configuration.

CXXFLAGS+= -std=c++11

ifndef CMECDRIVERDIR
  $(error CMECDRIVERDIR is not defined)
endif

# Add the source directories to the include path
CXXFLAGS+= -I$(CMECDRIVERDIR)/src/base -I$(CMECDRIVERDIR)/src/contrib

###############################################################################
# Configuration-dependent configuration.

ifeq ($(OPT),TRUE)
  # NDEBUG disables assertions, among other things.
  CXXFLAGS+= -O3 -DNDEBUG 
  F90FLAGS+= -O3
else
  CXXFLAGS+= -O0
  F90FLAGS+= -O0 
endif

ifeq ($(DEBUG),TRUE)
  # Frame pointers give us more meaningful stack traces in OPT+DEBUG builds.
  CXXFLAGS+= -ggdb -fno-omit-frame-pointer
  F90FLAGS+= -g
endif

# DO NOT DELETE
