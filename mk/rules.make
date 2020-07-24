# Rules for compiling object files

# Compilation directories
DEPDIR= $(CURDIR)/depend
BUILDDIR= $(CURDIR)/build

# Dependency file construction
MAKEDEPENDCPP= \
    mkdir -p $(DEPDIR); \
    echo "-- Generating dependencies for $<"; \
    $(CXX) -M $(CXXFLAGS) $(CURDIR)/$< > $(DEPDIR)/$*.P; \
    sed -e 's~.*:~$(BUILDDIR)/$*.o $(DEPDIR)/$*.d:~' < $(DEPDIR)/$*.P > $(DEPDIR)/$*.d; \
    sed -e 's/.*://' -e 's/\\$$//' < $(DEPDIR)/$*.P | fmt -1 | sed -e 's/^ *//' -e 's/$$/:/' >> $(DEPDIR)/$*.d; \
    rm -f $(DEPDIR)/$*.P

# Compilation rules
$(BUILDDIR)/%.o : %.cpp
	@mkdir -p $(@D)
	@$(MAKEDEPENDCPP)
	$(CXX) $(CXXFLAGS) -c -o $@ $(CURDIR)/$<

# DO NOT DELETE
