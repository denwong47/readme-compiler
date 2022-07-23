COMMIT_MESSAGE := $(if $(COMMIT_MESSAGE),$(COMMIT_MESSAGE),)

remap_githook:
	git config core.hooksPath .githooks/hooks

commit: remap_githook
	@if test -z "$(COMMIT_MESSAGE)"; then echo Write your commit message:; read COMMIT_MESSAGE; fi; git commit -a -m "$$COMMIT_MESSAGE"

push: commit
	git push