# Base directory.
CMECDRIVERDIR= ../..

# Load Makefile framework. 
include $(CMECDRIVERDIR)/mk/framework.make

FILES= tinyxml2.cpp

LIB_TARGET= libcmeccontrib.a

.PHONY: all clean

# Build rules. 
all: $(LIB_TARGET)

$(LIB_TARGET): $(FILES:%.cpp=$(BUILDDIR)/%.o)
	rm -f $(LIB_TARGET)
	ar -cqs $(LIB_TARGET) build/*.o

# Clean rules.
clean:
	rm -f $(LIB_TARGET) 
	rm -rf $(DEPDIR)
	rm -rf $(BUILDDIR)

# Include dependencies.
-include $(FILES:%.cpp=$(DEPDIR)/%.d)

# DO NOT DELETE
