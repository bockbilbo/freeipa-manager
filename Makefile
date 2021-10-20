# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright (C) 2021  Unai Goikoetxeta

.DEFAULT: help
SHELL:= /bin/bash

APT:= apt update && apt install -y --no-install-recommends python3 python3-pip libsasl2-dev python3-dev libldap2-dev libssl-dev
DNF:= dnf install -y python3 python3-pip python3-devel openldap-devel

DESTDIR:= /opt/freeipa_manager
SYMLINK:= /usr/sbin/freeipa_manager
REDHATOS:= $(wildcard /etc/redhat-release*)
DEBIANOS:= $(wildcard /etc/debian_version*)

ifneq ($(DEBIANOS),)
PKG_INSTALLER:= $(APT)
else ifneq ($(REDHATOS),)
PKG_INSTALLER:= $(DNF)
endif

help:
	@echo "make help"
	@echo "       displays this menu"
	@echo "make install-system-dependencies"
	@echo "       installs system dependencies required to run the program"
	@echo "make install"
	@echo "       installs the program"
	@echo "make update"
	@echo "       updates the program"
	@echo "make uninstall"
	@echo "       uninstalls the program"

install-system-dependencies:
	$(PKG_INSTALLER)
	pip3 install -r requirements.txt

install:
	mkdir $(DESTDIR)
	mkdir $(DESTDIR)/cache
	cp freeipa_manager.py $(DESTDIR)/
	cp config.yaml $(DESTDIR)/
	cp -Rf templates/ $(DESTDIR)/
	cp -Rf utils/ $(DESTDIR)/
	chgrp -Rf admins $(DESTDIR)
	chmod 775 -Rf $(DESTDIR)
	chmod g+s $(DESTDIR)
	chmod g+s $(DESTDIR)/cache/
	setfacl -d -m group:admins:rwx $(DESTDIR)
	setfacl -d -m group:admins:rwx $(DESTDIR)/cache/
	chmod +x $(DESTDIR)/freeipa_manager.py
	ln -s $(DESTDIR)/freeipa_manager.py $(SYMLINK)

uninstall:
	rm -Rf $(DESTDIR)
	rm $(SYMLINK)

update:
	cp freeipa_manager.py $(DESTDIR)/
	cp config.yaml $(DESTDIR)/
	cp -Rf templates/* $(DESTDIR)/templates/
	cp -Rf utils/* $(DESTDIR)/utils/
	chgrp -Rf admins $(DESTDIR)
	chmod 775 -Rf $(DESTDIR)
	chmod +x $(DESTDIR)/freeipa_manager.py
