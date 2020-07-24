# Base directory.
CMECDRIVERDIR=..

# Load Makefile framework. 
include $(CMECDRIVERDIR)/mk/framework.make

BUILD_TARGETS+= base contrib
CLEAN_TARGETS= $(addsuffix .clean,$(BUILD_TARGETS))

CMECDRIVERLDFLAGS+= -L$(CMECDRIVERDIR)/src/base -L$(CMECDRIVERDIR)/src/contrib -lcmecbase -lcmeccontrib

EXEC_FILES= cmec-driver.cpp

EXEC_TARGETS= $(EXEC_FILES:%.cpp=%)

FILES= $(UTIL_FILES) $(EXEC_FILES)

.PHONY: all clean $(BUILD_TARGETS)

# Build rules. 
all: $(BUILD_TARGETS) $(EXEC_TARGETS)

$(BUILD_TARGETS): %:
	cd $*; $(MAKE)

$(EXEC_TARGETS): %: $(BUILD_TARGETS) $(BUILDDIR)/%.o $(CMECDRIVERLIBS)
	$(CXX) $(LDFLAGS) $(CMECDRIVERLDFLAGS) -o $@ $(UTIL_FILES:%.cpp=$(BUILDDIR)/%.o) $(BUILDDIR)/$*.o $(LIBRARIES)
	mv $@ $(CMECDRIVERDIR)/bin

# Clean rules.
clean: $(CLEAN_TARGETS)
	rm -rf $(DEPDIR)
	rm -rf $(BUILDDIR)

$(CLEAN_TARGETS): %.clean:
	cd $*; $(MAKE) clean

# Include dependencies.
-include $(FILES:%.cpp=$(DEPDIR)/%.d)

# DO NOT DELETE
