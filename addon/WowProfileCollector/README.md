# WowProfileCollector

Small local addon for `wow-profile`.

Install by copying the `WowProfileCollector` folder into your Retail AddOns folder:

```text
World of Warcraft\_retail_\Interface\AddOns\WowProfileCollector
```

The addon captures automatically shortly after character login and again during character logout. To force a capture while testing, run:

```text
/wowprofile capture
```

WoW writes the captured data to the account SavedVariables file after logout or UI reload:

```text
World of Warcraft\_retail_\WTF\Account\<account>\SavedVariables\WowProfileCollector.lua
```
