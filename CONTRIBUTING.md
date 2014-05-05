Contributing Changes to 1flow
-----------------------------

Contribution areas are listed in `AUTHORS.md` and there is an [official list of issues we need external help on][helpneeded]. If you have any other idea, feel free to [suggest it on IRC][irc].

Contributing to the project is both welcomed and encouraged. To do so, you have at least two options:

# Hacking the code directly

- Fork the project.
- Create a branch for your changes.
- Modify the files as appropriate.
	- if you want to contribute a translation/localization, see below.
- Make `flake8` happy on your modified files;
	- you can ignore `["E221", "E241", "E272"]`, I do.
	- Please, remove trailing spaces/tabs at the end of *any* line.
-  Update documentation (you can do it via the Django admin for a friendly-editing interface, it's the `Help contents` section) :
	- if you add/change any user-visible feature, update the “features” documentation in english, if not sure of your english, feel free to ask on the IRC channel.
		- If you are not english native, be kind enough to update the translated version in your native language.
		- eventually ping on IRC for other developpers, it's best if we can gather all translations before accepting the patch.
	- If you change anything related to the documented architecture, update it in the `docs/` folder.
- Add tests to the following files and follow their format/conventions:
    - `{base,core}/tests/test_*.py`
-  Obviously, make sure all tests pass. Sorry for having asked it. Just run `make test` and enjoy whatever pleases you.
- Push your branch to `GitHub` and submit a pull request,
- Wait for my neurons to connect.


## Translations / localizations

Currently, 1flow uses `django-rosetta`, available at your local address [http://localhost:8000/translate/](http://localhost:8000/translate/).

In the code, there are 2 ways to create i18n strings:

- the old, with plain english sentences and a lot of `%s`. **Please do not use this anymore** and use the new instead:
- the new, where even english localization is available to translators. i18n strings are “codes”, like `exception.article.cannot_set_title`, `info.article.title_changed(%(article_id)s, %(old_title)s, %(new_title)s)`, `label.import_url.urls_list` and so on. Python code examples:

    LOGGER.exception(u'exception.article.cannot_extract_title('
                             u'%(article)s)', article=self)

    LOGGER.info(u'info.article.changed_title(%(article_id)s, '
                        u'%(old_title)s, %(new_title)s)',
                        article_id=self.id, old_title=old_title,
                        new_title=self.title)

More examples in Django templates will come as soon as we implement some.

Important: **we now always use named arguments in i18n strings, for more translators understanding of translatable strings.**

The new form is not yet widespread, we replace old instances while time passes. Please use it in any new code you create. If you fix bugs on existing code, please also convert messages, but in separate commits.


# Or submitting issues / feedback

If you don't feel comfortable forking the project or modifying it, you can also [submit an issue](https://github.com/1flow/1flow/issues) that includes the appropriate request.

If you found a bug, please include anything that can help us reproduce it, **excluding any of your passwords**. Never give them to anybody. If we need to access some of your personal data for any reason, we will discuss it first, and ask for something like a read-only/partial-display screen-sharing with your approval.

If you are not a developer and do not feel comfortable on `GitHub`, Just use the feedback form on http://1flow.io/ to submit ideas and feedback, we (developpers)
will do our best to integrate them in our workflow.

Thanks!


  [irc]: irc://chat.freenode.net/#1flow
  [helpneeded]: https://github.com/1flow/1flow/issues?labels=needs+help&page=1&state=open
