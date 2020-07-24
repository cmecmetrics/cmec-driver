# Makefile (cmec-driver)

BUILD_TARGETS= src
CLEAN_TARGETS= $(addsuffix .clean,$(BUILD_TARGETS))

.PHONY: all clean $(BUILD_TARGETS) $(CLEAN_TARGETS)

# Build rules.
all: $(BUILD_TARGETS)

$(BUILD_TARGETS): %:
	cd $*; $(MAKE)

# Clean rules.
clean: $(CLEAN_TARGETS)
	rm -f bin/*

$(CLEAN_TARGETS): %.clean:
	cd $*; $(MAKE) clean

# DO NOT DELETE
