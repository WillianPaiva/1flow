


# 1flow — libre information platform

This project is about reading and writing on the web, while keeping your data safe and sharing it with friends and colleagues.

It can be seen as the merge of the most-valuable features of Feedly/Readability (implemented) and Facebook/Twitter/Medium/Digg/Storify/ScoopIT/Flickr (on the way) in one application. Obviously 1flow offers less bells-and-whistles, its main feature being the global integration of all others (and probably the fact that it's libre software).

It has some similarities with a cloud storage, and could perhaps implement a compatible API.

Your data is stored on your own server (or one mutualized with friends or colleagues). Inter-server communication will be implemented via [the GnuPG web of trust][kgpg].

You'll find a more user-oriented original pitch at http://1flow.io/ and project news [on the official blog][1blog].

1flow development is [funded via Gittip][gittip].



# Installation

**Please, [see the wiki](/1flow/1flow/wiki/Installation).**



## Future plans

I'm thinking about creating a `docker` container to get a development environment already setup in one command. Checkout the `feature/installable` branch for up-to-date code and documentation of this task.

If you are interested in helping out, I will be glad to hear from you and help. Please get in touch via [Twitter](https://twitter.com/Karmak23) or [IRC][irc].



# Current status

The current implementation is fully usable, for what's done.

**It's in production on [1flow.io](http://1flow.io/) and the early adopters use it since April 2013.**

1flow takes benefit of continuous integration: new features and bug fixes are pushed very regularly.

As [1flow.io](http://1flow.io/) is my currently my personal server and not a company project, you won't get a free account there. I have limited resources, and there are legal issues – at least in France – that I do not want to deal with, and which are completely avoided by using your own 1flow instance.

Nevertheless, project contributors will eventually get an access once we meet IRL and have established a trusted relationship. Note that it is still at my discretion in the end.



# License

1flow is released under the GNU Affero GPL v3. See the `COPYING` file for details.



# Project management and contact

Public project management (features specification, general planned actions, agile iteration content proposals) [happens on Trello][trello], backed with the [IRC channel][irc], video conferences and physical meetups. Issues (bugs) are tracked [on GitHub][ghiss]. These are the authoritative working tools.

Public announcements are broadcasted [on the 1flow tumblr][tumblr] and automatically relayed on the [Twitter feed][twitter], where sporadic news and small status updates are posted.

There is a user support forum at http://1flow.userecho.com/ but it's not used for development at all.

`AUTHORS.md` holds the list of authors and all contributors, a short – and not exhaustive – list of their contributions to the project. **It also contains a list of some of the project needs.**

`CONTRIBUTING.md` explicits developer guidelines and *how* to contribute.

Prior version 0.26, 1flow was a startup project. Since version 0.26, I consider the code suited for FOSS development, but I could have missed some pieces. Please yield anything you find unclear.

Note for developers: this is a `git-flow` repository, we follow the [successful branching model](http://nvie.com/posts/a-successful-git-branching-model/).

Thanks for reading ;-)


  [lunch]: https://github.com/mperham/lunchy
  [gittip]: https://gittip.com/1flow/
  [ghiss]: https://github.com/1flow/1flow
  [1blog]: http://blog.1flow.io/
  [kgpg]: http://oliviercortes.com/principles-human-trusted-machines-distributed-network.html
  [twitter]: https://twitter.com/1flow_io
  [tumblr]: http://blog.1flow.io/
  [trello]: https://trello.com/b/lSR7Y6Vi/1flow-features-development
  [irc]: irc://chat.freenode.net/#1flow
