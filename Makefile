# Do things in edx-platform

clean:
	# Remove all the git-ignored stuff, but save and restore things marked
	# by start-noclean/end-noclean.
	sed -n -e '/start-noclean/,/end-noclean/p' < .gitignore > /tmp/private-files
	tar cf /tmp/private.tar `git ls-files --exclude-from=/tmp/private-files --ignored --others`
	git clean -fdX
	tar xf /tmp/private.tar


i18n_extract:
	pip install git+https://github.com/lukin0110/poeditor-client@poeditor-client==0.0.6

	paver i18n_validate_transifex_config
	paver i18n_generate

	python ./scripts/skim.py

	poeditor --sync-terms pushTerms
	@echo " == Pushed strings to POEditor.com"
