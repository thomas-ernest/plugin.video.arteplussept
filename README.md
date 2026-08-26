# Arte +7

<p align="center">
  <img src="https://github.com/thomas-ernest/plugin.video.arteplussept/blob/master/plugin.video.arteplussept/resources/icon.png" alt="Arte +7 logo">
</p>

## Description

Plugin "plugin.video.arteplussept" to browse Arte content and watch it in multiple languages and subtitles on Kodi (ex XBMC).
Can be used without or with Arte account in order to benefit from a better cross-device experience. For instance starting a video or a serie on the mobile app and resume it on kodi or to share same favorites.

### Features

- Browse and watch Arte replays
- Watch Arte live stream
- Watch Arte content in multiple languages and subtibles
- Search for content on Arte
- Browse or search multi-page content
- Play serie as a playlist or browse serie as a menu.
- Resume a serie from the first not completed episode thanks to Arte history (login required)
- Load serie as a playlist, when watching one of its episode
- Login with your Arte account without storing password on filesystem - only the token 
- Login with basic (user password) or device flow authentication method
- Manage - view or purge - your Arte history (login required)
- Manage - view, add, delete or purge - your Arte favorites (login required)
- Supported language : DE, EN, FR, IT, PL, RO

### Not (very well) supported
- Resume videos from where you stopped them (cross device) (login required)
- Geo blocking
- Display of availability / broadcasting dates

For feature requests or reporting issues go [here](https://github.com/thomas-ernest/plugin.video.arteplussept/issues).

# Donation

The extension is free. Nevertheless, any donation will motivate me to maintain it.
Various donation methods are listed at https://thomas-ernest.github.io/

# Contributing

Contributions are welcome !
You may look at the [issues](https://github.com/thomas-ernest/plugin.video.arteplussept/issues) or unsupported features above.

## Install the addon locally

Follow the steps bellow depending on your system and software version

### 1. Open the addons folder

Kodi is installed on a different path according to the operating system it is installed on. You can refer to [this page](https://kodi.wiki/view/Kodi_data_folder). Go to $KODI_FOLDER/addons/

### 2. Dowload the addon

In Kodi addons folder
- clone this repository or one of if its forks (preferred) and copy source to plugin folder
  - `git clone https://github.com/thomas-ernest/plugin.video.arteplussept.git`
  - `cp plugin.video.arteplussept/plugin.video.arteplussept $KODI_HOME/addons/`
- or download the plugin :
  - [any release](https://github.com/thomas-ernest/plugin.video.arteplussept/releases)
  - [latest commit on master](https://github.com/thomas-ernest/plugin.video.arteplussept/archive/refs/heads/master.zip)
  - use Kodi UI to install from zip

### 3. Install the addon

- If you downloaded a zip, extract the content of the zip in the `$KODI_HOME/addons` folder.
- Make sure that the addon is in folder `plugin.video.arteplussept` (and not `plugin.video.arteplussept-master` if you downloaded the latest commit of master for instance or in 
`plugin.video.arteplussept/plugin.video.arteplussept` if you missed the mv or cp operation).

For instance for Linux:
```
unzip -x plugin.video.arteplussept-master.zip
mv plugin.video.arteplussept plugin.video.arteplussept-backup OR rm -fr plugin.video.arteplussept
mv plugin.video.arteplussept-master plugin.video.arteplussept
```

### 4. Enjoy

* Done ! The plugin should show up in your video add-ons section.

## Troubleshooting

If you get an issue after a fresh manual installation, you should try
either to restart in order to install dependencies automatically
either to install the dependancies manually. The dependancies are :

* requests (script.module.requests)
* dateutil (script.module.dateutil)
* adaptative inputstream (inputstream.adaptive)

They should be in the "addon libraries" section of the official repository.

If you are having issues with the add-on, you can open a issue and join your log file. The log file will contain your system user name and sometimes passwords of services you use in the software, so you may want to sanitize it beforehand. Detailed procedure [here](http://kodi.wiki/view/Log_file/Easy).

## Coding

- Compatible with python 3 only and Kodi Matrix (based on Python 3.8) since version 1.1.5
- Coding guideline :
  - 4 space indentation. No tab.
  - Snake case for variables and methods
  - No parenthesis around keywords like if, elif, for, while...
  - Spaces around = when used in body and script. No space around = when setting method parameters
  - Double quotes for strings used to end_users or logs.
  - Single quotes for dict indices and strings for internal purpose.
  - Object oriented (preferred), not fully applied given original 
  - Pylint guidelines : pydoc for every module and methods...
  - Flake8 guidelines except line length is 100 instead of 79.
- Pylint and Flake8 are run in CI. You might want to install them on your local env.

## Releasing

### Releasing part on contributor's host

Steps to be followed by a contributor to create a release.
Preferablly you can use scripts/create-release.sh in a BASH to do the same.
It has a parameter --no-push, if you want to check the results before applying changes remotely.

- Releases are in master branch. Make sure HEAD in master reflects the content of the next release.
- Set the version $MAJOR.$MINOR.$BUGFIX (without v) in addon.xml /addon/@version 
- Describe the changes of the news version in:
    - CHANGELOG.md. Ignore changelog.txt remaining here for legacy purpose.
    - addon.xml /addon/extension[@point="xbmc.addon.metadata"]/news. Ensure it counts less than 1500 chars.
- Create a commit with version bump
    - git add addon.xml CHANGELOG.md && git commit -m "Bump version to $MAJOR.$MINOR.$BUGFIX"
- Create and push tag "vMaj.Min.Bug" (with v) to GitHub in order to create a GitHub release and submit a [PR to official XBMC repo](https://github.com/xbmc/repo-plugins/pulls) with the CI.
    - git tag -a v$MAJOR.$MINOR.$BUGFIX
    - Fill the tag message with the description of the changes of the news version. It will be used as GitHub release notes.
    - git push origin --tags

### Releasing part in CI

Steps run automatically by CI, with troubleshooting guide.

- "Kodi Addon-Submitter" in CI is in charge of:
    - creating a GitHub release with version $MAJOR.$MINOR.$BUGFIX in https://github.com/thomas-ernest/plugin.video.arteplussept/releases
    - submitting a new version to official Kodi repository
        - One-commit change in matrix branch https://kodi.wiki/view/Submitting_Add-ons
        - Open pull-request to official repo https://github.com/xbmc/repo-plugins/pulls
- if the action "Kodi Addon-Submitter" in CI  fails, refresh the token value in action secret.
    - In https://github.com/settings/tokens/ generate a corsed-grained token KODI_SUBMITTER_TOKEN_CLASSIC and copy its value
    - set the token value in action secret KODI_SUBMITTER_TOKEN https://github.com/thomas-ernest/plugin.video.arteplussept/settings/secrets/actions
    - Re-run the failing job "Kodi Addon-Submitter"

## Testing

Failing the major migration out of xbmcswift2 and HBB TV API, component tests are broken.

1.  **Install dependencies**:
    ```bash
    pip install -r requirements-test.txt
    ```
2.  **Run all tests**:
    In plugin root folder
    ```bash
    PYTHONPATH="$PWD/plugin.video.arteplussept;" python -m pytest -vv tests/test_lib_mapper_arteliveitem.py
    ```
    
various docs and examples
# https://github.com/eral/kodi.plugin.video.u-next-animefree-eral-test/blob/master/tests/script_addon_router_for_kodi_test.py
# https://github.com/firsttris/plugin.video.sendtokodi/tree/master/tests
# https://github.com/sbroenne/plugin.video.nhkworldtv/tree/main/plugin.video.nhkworldtv/tests
# https://github.com/audiosistem/Bee-Queen/blob/main/matrix/plugin.video.jacktook/GEMINI.md?plain=1

## Route graph

Previous conceptual route graph, from before the major migration. Menu/list-item routes are blue, video playback routes are green, and background actions are orange.

```mermaid
graph LR
  index["index (menu)"]
  api_category["api_category (menu)"]
  cached_category["cached_category (menu)"]
  category_page["category_page (menu)"]
  favorites_default["favorites_default (menu)"]
  favorites["favorites (menu)"]
  add_favorite["add_favorite (action)"]
  remove_favorite["remove_favorite (action)"]
  purge_favorites["purge_favorites (action)"]
  mark_as_watched["mark_as_watched (action)"]
  last_viewed_default["last_viewed_default (menu)"]
  last_viewed["last_viewed (menu)"]
  purge_last_viewed["purge_last_viewed (action)"]
  collection["collection (menu)"]
  streams["streams (menu)"]
  play_live["play_live (video)"]
  play["play (video)"]
  play_from["play_from (video)"]
  play_specific["play_specific (video)"]
  play_collection["play_collection (video)"]
  init_search["init_search (menu)"]
  search["search (menu)"]
  user_login["user_login (action)"]
  user_logout["user_logout (action)"]

  index <--> api_category
  index <--> cached_category
  index <--> category_page
  index <--> favorites_default
  index <--> last_viewed_default
  index <--> collection
  index <--> init_search
  index <--> user_login
  index <--> user_logout

  favorites_default <--> favorites
  favorites -->|if authenticated| add_favorite
  favorites -->|if authenticated| remove_favorite
  favorites -->|if authenticated| purge_favorites
  favorites -->|if authenticated| mark_as_watched

  last_viewed_default <--> last_viewed
  last_viewed -->|if authenticated| purge_last_viewed

  collection <-->|if playable item| play
  collection <-->|if playable item| play_from
  collection <-->|if playable item| play_specific
  collection <-->|if collection item| play_collection
  collection <--> streams
  streams <-->|if playable item| play
  favorites <-->|if playable item| play
  favorites <-->|if playable item| play_from
  favorites <-->|if playable item| play_specific
  favorites <-->|if collection item| play_collection
  search <-->|if playable item| play
  search <-->|if playable item| play_from
  search <-->|if playable item| play_specific
  search <-->|if collection item| play_collection
  play -->|play context| play_from
  play_from -->|audio selection| play_specific
  init_search -->|search results| search

  classDef menu fill:#dbeafe,stroke:#1d4ed8,color:#0f172a;
  classDef video fill:#dcfce7,stroke:#16a34a,color:#052e16;
  classDef action fill:#fef3c7,stroke:#d97706,color:#451a03;

  class index,api_category,cached_category,category_page,favorites_default,favorites,last_viewed_default,last_viewed,collection,streams,init_search,search menu;
  class play_live,play,play_from,play_specific,play_collection video;
  class add_favorite,remove_favorite,purge_favorites,mark_as_watched,purge_last_viewed,user_login,user_logout action;
```

Current route graph, based on the routes defined in `plugin.py`. Menu/list-item routes are blue, video playback routes are green, and background or context-menu actions are orange. Bidirectional edges represent navigation from a menu item to another route and return to the originating menu context. One-way edges represent context-menu actions or direct plugin URL navigation.

```mermaid
graph LR
  index["/ (index, menu)"]
  category_page["/category/page/... (category_page, menu)"]
  raw_page["/raw_page/... (raw_page, menu)"]
  favorites_default["/favorites (favorites_default, menu)"]
  favorites["/favorites/<page> (favorites, menu)"]
  last_viewed_default["/last_viewed (last_viewed_default, menu)"]
  last_viewed["/last_viewed/<page> (last_viewed, menu)"]
  collection["/collection/<program_id> (collection, menu)"]
  init_search["/search (init_search, menu)"]
  search["/search/<zone_id>/<page>/<query> (search, menu)"]
  play_live["/play/live/... (play_live, video)"]
  play["/play/<program_id>/... (play, video)"]
  play_collection["/play/collection/<col_id>/... (play_collection, video)"]
  play_collection_from["/play/collection/<col_id>/.../from/<prgm_id> (play_collection_from, video)"]
  add_favorite["/add_favorite/... (add_favorite, action)"]
  remove_favorite["/remove_favorite/... (remove_favorite, action)"]
  purge_favorites["/purge_favorites (purge_favorites, action)"]
  mark_as_watched["/mark_as_watched/... (mark_as_watched, action)"]
  purge_last_viewed["/purge_last_viewed (purge_last_viewed, action)"]
  user_login["/user/login (user_login, action)"]
  user_logout["/user/logout (user_logout, action)"]

  index <--> category_page
  index <--> favorites_default
  index <--> last_viewed_default
  index <--> init_search
  index <-->|live item| play_live
  index -->|login menu action| user_login
  index -->|logout menu action| user_logout

  category_page <--> category_page
  category_page -->|external category| raw_page
  category_page <-->|video item| play
  category_page <-->|collection item| collection
  category_page <-->|collection playlist| play_collection

  favorites_default <--> favorites
  favorites <--> favorites
  favorites <-->|video item| play
  favorites <-->|collection item| collection
  favorites <-->|collection playlist| play_collection
  favorites -->|context menu| add_favorite
  favorites -->|context menu| remove_favorite
  favorites -->|context menu| mark_as_watched
  favorites -->|purge action| purge_favorites

  last_viewed_default <--> last_viewed
  last_viewed <--> last_viewed
  last_viewed <-->|video item| play
  last_viewed <-->|collection item| collection
  last_viewed <-->|collection playlist| play_collection
  last_viewed -->|purge action| purge_last_viewed

  raw_page <-->|video item| play
  raw_page <-->|collection item| collection
  raw_page <-->|collection playlist| play_collection
  collection <-->|video item| play
  collection <-->|playlist from selected item| play_collection_from
  collection <-->|collection item| collection

  init_search <--> search
  search <--> search
  search <-->|video item| play
  search <-->|collection item| collection
  search <-->|collection playlist| play_collection

  classDef menu fill:#dbeafe,stroke:#2563eb,color:#172554;
  classDef video fill:#dcfce7,stroke:#16a34a,color:#14532d;
  classDef action fill:#ffedd5,stroke:#ea580c,color:#7c2d12;

  class index,category_page,raw_page,favorites_default,favorites,last_viewed_default,last_viewed,collection,init_search,search menu;
  class play_live,play,play_collection,play_collection_from video;
  class add_favorite,remove_favorite,purge_favorites,mark_as_watched,purge_last_viewed,user_login,user_logout action;
```
