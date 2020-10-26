# Makefile to generate working environment for Ops

# used to determine arch for downloads
UNAME := $(shell uname | tr '[:upper:]' '[:lower:]')

ACTIVATE_BIN := venv/bin/activate

all: $(ACTIVATE_BIN) pip_requirements 

clean:
	$(RM) -r venv
	find . -name "*.pyc" -exec $(RM) -rf {} \;

$(ACTIVATE_BIN):
	python3 -m venv venv
	chmod +x $@

pip_requirements: $(ACTIVATE_BIN) requirements.txt
	. venv/bin/activate; PYTHONWARNINGS='ignore:DEPRECATION' pip3 install -r requirements.txt 

freeze: requirements.txt
	pip freeze > requirements.txt
