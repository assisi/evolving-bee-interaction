PYLON_ROOT ?= /opt/pylon5
CPPFLAGS   += $(shell $(PYLON_ROOT)/bin/pylon-config --cflags)
LDFLAGS    += $(shell $(PYLON_ROOT)/bin/pylon-config --libs-rpath)
LDLIBS     += $(shell $(PYLON_ROOT)/bin/pylon-config --libs)

all:

pylon/pylonconfig: pylon/pylonconfig.o

pylon/pylonrecord: pylon/pylonserverrecord.o

clean:
	find . '(' -name '*.pyc' -o -name '*~' ')' -delete
	make -C ./doc/ clean
