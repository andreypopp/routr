.PHONY: docs

docs:
	$(MAKE) -C ./docs html

test develop install register clean build:
	python setup.py $@

release:
	python setup.py sdist upload
