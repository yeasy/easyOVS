PROJ = easyovs

#DO NOT CHANGE THE FOLLOWING PART

SRCFILES = $(PROJ)/*.py
TESTFILES = $(PROJ)/test/*.py
EXAMPLES = $(PROJ)/examples/*.py
EXEC = bin/$(PROJ)
MANPAGES = $(PROJ).1
PYSRC = $(SRCFILES) $(TESTFILES) $(EXAMPLES) $(EXEC)
P8IGN = E251,E201,E302,E202
BINDIR = /usr/bin
MANDIR = /usr/share/man/man1
DOCDIRS = doc/html doc/latex
PDF = doc/latex/refman.pdf

CFLAGS += -Wall -Wextra

all: codecheck test

codecheck: $(PYSRC)
	-echo "Running code check"
	util/versioncheck.py
	pyflakes $(PYSRC)
	pylint --rcfile=.pylint $(PYSRC)
	pep8 --repeat --ignore=$(P8IGN) $(PYSRC)

errcheck: $(PYSRC)
	-echo "Running check for errors only"
	pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)

test: $(SRCFILES) $(TESTFILES)
	-echo "Running tests"

develop: $(MANPAGES)
	# Perhaps we should link these as well
	install $(MANPAGES) $(MANDIR)
	python setup.py develop

man: $(MANPAGES)

$(MANPAGES): $(EXEC)
	PYTHONPATH=. help2man -N -n "Manpages." $< -o $@

.PHONY: doc clean install uninstall

install: #$(MANPAGES)
	#install $(MANPAGES) $(MANDIR)
	python setup.py install  --record install.log

uninstall:
	[ -e install.log ] && cat install.log | xargs rm -rf

clean:
	rm -rf build dist *.egg-info *.1 $(MANPAGES) $(DOCDIRS)
	find . -name "*.pyc"|xargs rm -f

doc: man
	doxygen doc/doxygen.cfg
	make -C doc/latex
