.PHONY: all clean deps test build appimage translations

APP_NAME = shoboi-tag-editor
VERSION = 0.1.0
ARCH = $(shell uname -m)
APPDIR = $(APP_NAME).AppDir
APPIMAGE = $(APP_NAME)-$(VERSION)-$(ARCH).AppImage
TRANSLATIONS_DIR = src/shoboi_tag_editor/translations

all: appimage

deps:
	uv sync
	uv add --dev pyinstaller

test:
	uv run pytest -v

translations:
	for ts in $(TRANSLATIONS_DIR)/*.ts; do \
		uv run python -m PyQt6.lupdate --help > /dev/null 2>&1 || true; \
		uv run python -c "from PyQt6.QtCore import QTranslator, QCoreApplication; \
			import subprocess; \
			subprocess.run(['lrelease', '$$ts'])" 2>/dev/null || \
		uv run pyside6-lrelease "$$ts" 2>/dev/null || \
		lrelease "$$ts" 2>/dev/null || \
		lrelease-qt6 "$$ts"; \
	done

build: deps translations
	uv run pyinstaller \
		--name $(APP_NAME) \
		--onedir \
		--windowed \
		--noconfirm \
		--add-data "$(TRANSLATIONS_DIR):shoboi_tag_editor/translations" \
		--paths src \
		--hidden-import PyQt6.sip \
		--collect-all PyQt6 \
		run.py

appimage: build
	rm -rf $(APPDIR)
	mkdir -p $(APPDIR)/usr/bin
	mkdir -p $(APPDIR)/usr/share/applications
	mkdir -p $(APPDIR)/usr/share/icons/hicolor/scalable/apps

	cp -r dist/$(APP_NAME)/* $(APPDIR)/usr/bin/
	cp $(APP_NAME).desktop $(APPDIR)/
	cp $(APP_NAME).desktop $(APPDIR)/usr/share/applications/
	cp $(APP_NAME).svg $(APPDIR)/
	cp $(APP_NAME).svg $(APPDIR)/usr/share/icons/hicolor/scalable/apps/

	# Create AppRun script
	echo '#!/bin/bash' > $(APPDIR)/AppRun
	echo 'SELF=$$(readlink -f "$$0")' >> $(APPDIR)/AppRun
	echo 'HERE=$${SELF%/*}' >> $(APPDIR)/AppRun
	echo 'export PATH="$${HERE}/usr/bin:$${PATH}"' >> $(APPDIR)/AppRun
	echo 'export LD_LIBRARY_PATH="$${HERE}/usr/bin:$${LD_LIBRARY_PATH}"' >> $(APPDIR)/AppRun
	echo 'exec "$${HERE}/usr/bin/$(APP_NAME)" "$$@"' >> $(APPDIR)/AppRun
	chmod +x $(APPDIR)/AppRun

	# Download appimagetool if not present
	if [ ! -f appimagetool-$(ARCH).AppImage ]; then \
		curl -L -o appimagetool-$(ARCH).AppImage \
			https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-$(ARCH).AppImage; \
		chmod +x appimagetool-$(ARCH).AppImage; \
	fi

	ARCH=$(ARCH) ./appimagetool-$(ARCH).AppImage $(APPDIR) $(APPIMAGE)

clean:
	rm -rf build dist $(APPDIR) *.spec
	rm -f $(APP_NAME)-*.AppImage
	rm -f appimagetool-*.AppImage
