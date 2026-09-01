local ADDON_NAME = ...
local ADDON_VERSION = "0.1.0"
local SCHEMA_VERSION = 1
local LOGIN_CAPTURE_DELAY_SECONDS = 5
local SPEC_CAPTURE_DELAY_SECONDS = 2
local EQUIPMENT_CAPTURE_DELAY_SECONDS = 1
local EQUIPMENT_SETS_CHANGED_DELAY_SECONDS = 1
local SPEC_RETRY_DELAY_SECONDS = 1
local DUPLICATE_CAPTURE_WINDOW_SECONDS = 3
local MAX_SPEC_CAPTURE_ATTEMPTS = 10
local lastCaptureKey
local lastCaptureTime = 0

local ACTION_BAR_BINDINGS = {
    ACTIONBUTTON = { base = 1, count = 12 },
    MULTIACTIONBAR1BUTTON = { base = 61, count = 12 },
    MULTIACTIONBAR2BUTTON = { base = 49, count = 12 },
    MULTIACTIONBAR3BUTTON = { base = 25, count = 12 },
    MULTIACTIONBAR4BUTTON = { base = 37, count = 12 },
}

local ITEM_LEVEL_SLOT_COUNT = 15
local ITEM_LEVEL_IGNORED_INVENTORY_SLOTS = {
    [4] = true,
    [19] = true,
}

local MODIFIER_BITS = {
    { bit = 1, name = "SHIFT" },
    { bit = 2, name = "CTRL" },
    { bit = 4, name = "ALT" },
}

local function BitBand(left, right)
    if bit and bit.band then
        return bit.band(left, right)
    end
    if bit32 and bit32.band then
        return bit32.band(left, right)
    end
    return left % (right + right) >= right and right or 0
end

local function EnsureDB()
    if type(WowProfileCollectorDB) ~= "table" then
        WowProfileCollectorDB = {}
    end

    WowProfileCollectorDB.schema_version = SCHEMA_VERSION
    WowProfileCollectorDB.addon_version = ADDON_VERSION
    WowProfileCollectorDB.characters = WowProfileCollectorDB.characters or {}
    return WowProfileCollectorDB
end

local function ModifiersFromMask(mask)
    local modifiers = {}
    mask = tonumber(mask) or 0

    for _, modifier in ipairs(MODIFIER_BITS) do
        if BitBand(mask, modifier.bit) ~= 0 then
            table.insert(modifiers, modifier.name)
        end
    end

    return modifiers
end

local function ActionSlotForCommand(command)
    for prefix, info in pairs(ACTION_BAR_BINDINGS) do
        local index = command:match("^" .. prefix .. "(%d+)$")
        if index then
            index = tonumber(index)
            if index and index >= 1 and index <= info.count then
                return info.base + index - 1
            end
        end
    end
    return nil
end

local function ResolveMacro(macroID)
    if not macroID or type(GetMacroInfo) ~= "function" then
        return nil
    end

    local name, icon, body = GetMacroInfo(macroID)
    return {
        id = macroID,
        name = name,
        icon = icon,
        body = body,
    }
end

local function ResolveSpell(spellID)
    if not spellID then
        return nil
    end

    local spell = { id = spellID }
    if C_Spell and C_Spell.GetSpellInfo then
        local info = C_Spell.GetSpellInfo(spellID)
        if info then
            spell.name = info.name
            spell.icon = info.iconID
            spell.original_icon = info.originalIconID
        end
    elseif type(GetSpellInfo) == "function" then
        local name, _, icon = GetSpellInfo(spellID)
        spell.name = name
        spell.icon = icon
    end
    return spell
end

local function ResolveItem(itemID)
    if not itemID then
        return nil
    end

    local item = { id = itemID }
    if type(C_Item) == "table" and C_Item.GetItemInfo then
        item.name = C_Item.GetItemInfo(itemID)
    elseif type(GetItemInfo) == "function" then
        item.name = GetItemInfo(itemID)
    end
    return item
end

local function ResolveActionSlot(slot)
    local actionType, id, subType = GetActionInfo(slot)
    local action = {
        slot = slot,
        type = actionType,
        id = id,
        sub_type = subType,
        text = type(GetActionText) == "function" and GetActionText(slot) or nil,
    }

    if actionType == "spell" or actionType == "flyout" or actionType == "pet" then
        action.spell = ResolveSpell(id)
    elseif actionType == "item" then
        action.item = ResolveItem(id)
    elseif actionType == "macro" then
        action.macro = ResolveMacro(id)
    end

    return action
end

local function CaptureClickBindings()
    local bindings = {}
    if not C_ClickBindings or not C_ClickBindings.GetProfileInfo then
        return bindings
    end

    for _, info in ipairs(C_ClickBindings.GetProfileInfo() or {}) do
        local spellID = info.spellID or info.actionID or info.id
        table.insert(bindings, {
            action = info.action,
            type = info.type,
            spell_id = spellID,
            spell = ResolveSpell(spellID),
            button = info.button,
            modifiers_mask = info.modifiers,
            modifiers = ModifiersFromMask(info.modifiers),
            raw = info,
        })
    end

    return bindings
end

local function CaptureKeyBindings()
    local bindings = {}
    if type(GetNumBindings) ~= "function" or type(GetBinding) ~= "function" then
        return bindings
    end

    for index = 1, GetNumBindings() do
        local bindingInfo = { GetBinding(index) }
        local command = bindingInfo[1]
        local category = bindingInfo[2]
        if command then
            local keys = {}
            for keyIndex = 3, #bindingInfo do
                if bindingInfo[keyIndex] then
                    table.insert(keys, bindingInfo[keyIndex])
                end
            end

            local slot = ActionSlotForCommand(command)
            table.insert(bindings, {
                index = index,
                command = command,
                category = category,
                keys = keys,
                primary_key = keys[1],
                secondary_key = keys[2],
                action_bar_slot = slot,
                action = slot and ResolveActionSlot(slot) or nil,
            })
        end
    end

    return bindings
end

local function CaptureActionBars()
    local slots = {}
    if type(GetActionInfo) ~= "function" then
        return slots
    end

    for slot = 1, 180 do
        local actionType = GetActionInfo(slot)
        if actionType then
            table.insert(slots, ResolveActionSlot(slot))
        end
    end

    return slots
end

local function CaptureItemLevel()
    if type(GetAverageItemLevel) ~= "function" then
        return nil
    end

    local averageItemLevel, equippedItemLevel, pvpItemLevel = GetAverageItemLevel()
    return {
        average = averageItemLevel,
        equipped = equippedItemLevel,
        pvp = pvpItemLevel,
    }
end

local function CopyArray(values)
    local result = {}
    if type(values) ~= "table" then
        return result
    end

    for index, value in pairs(values) do
        result[index] = value
    end
    return result
end

local function GetItemLinkFromEquipmentSetLocation(location)
    if type(location) ~= "number" or location < 0 or type(EquipmentManager_GetLocationData) ~= "function" then
        return nil
    end

    local locationData = EquipmentManager_GetLocationData(location)
    if type(locationData) ~= "table" then
        return nil
    end

    if locationData.isBags and locationData.bag and locationData.slot then
        if C_Container and C_Container.GetContainerItemLink then
            return C_Container.GetContainerItemLink(locationData.bag, locationData.slot)
        end
        if type(GetContainerItemLink) == "function" then
            return GetContainerItemLink(locationData.bag, locationData.slot)
        end
    elseif locationData.slot then
        return GetInventoryItemLink("player", locationData.slot)
    end

    return nil
end

local function GetDetailedItemLevel(itemLink)
    if not itemLink then
        return nil
    end
    if C_Item and C_Item.GetDetailedItemLevelInfo then
        return C_Item.GetDetailedItemLevelInfo(itemLink)
    end
    if type(GetDetailedItemLevelInfo) == "function" then
        return GetDetailedItemLevelInfo(itemLink)
    end
    return nil
end

local function CaptureEquipmentSetItemLevels(itemIDs, itemLocations, ignoredSlots)
    local slots = {}
    local total = 0
    local count = 0

    for inventorySlot = 1, 19 do
        local itemID = itemIDs and itemIDs[inventorySlot] or nil
        local ignored = (ignoredSlots and ignoredSlots[inventorySlot]) or ITEM_LEVEL_IGNORED_INVENTORY_SLOTS[inventorySlot] or false
        local location = itemLocations and itemLocations[inventorySlot] or nil
        local itemLink = GetItemLinkFromEquipmentSetLocation(location)
        local itemLevel = GetDetailedItemLevel(itemLink)

        slots[inventorySlot] = {
            inventory_slot = inventorySlot,
            item_id = itemID,
            location = location,
            ignored = ignored,
            item_level = itemLevel,
        }

        if itemID and itemLevel and not ignored then
            total = total + itemLevel
            count = count + 1
        end
    end

    return {
        equipped = count > 0 and (total / count) or nil,
        counted_slots = count,
        expected_slots = ITEM_LEVEL_SLOT_COUNT,
        slots = slots,
    }
end

local function CaptureEquipmentSets()
    local sets = {}
    if not C_EquipmentSet or not C_EquipmentSet.GetEquipmentSetIDs then
        return sets
    end

    for _, setID in ipairs(C_EquipmentSet.GetEquipmentSetIDs() or {}) do
        local name, iconFileID, returnedSetID, isEquipped, numItems, numEquipped, numInInventory, numLost, numIgnored =
            C_EquipmentSet.GetEquipmentSetInfo(setID)
        local assignedSpecIndex
        local assignedSpecID
        local assignedSpecName

        if C_EquipmentSet.GetEquipmentSetAssignedSpec then
            assignedSpecIndex = C_EquipmentSet.GetEquipmentSetAssignedSpec(setID)
            if assignedSpecIndex then
                assignedSpecID, assignedSpecName = GetSpecializationInfo(assignedSpecIndex)
            end
        end

        local itemIDs = CopyArray(C_EquipmentSet.GetItemIDs and C_EquipmentSet.GetItemIDs(setID) or nil)
        local itemLocations = CopyArray(C_EquipmentSet.GetItemLocations and C_EquipmentSet.GetItemLocations(setID) or nil)
        local ignoredSlots = CopyArray(C_EquipmentSet.GetIgnoredSlots and C_EquipmentSet.GetIgnoredSlots(setID) or nil)

        table.insert(sets, {
            id = returnedSetID or setID,
            name = name,
            icon_file_id = iconFileID,
            is_equipped = isEquipped,
            assigned_spec_index = assignedSpecIndex,
            assigned_spec_id = assignedSpecID,
            assigned_spec_name = assignedSpecName,
            num_items = numItems,
            num_equipped = numEquipped,
            num_in_inventory = numInInventory,
            num_lost = numLost,
            num_ignored = numIgnored,
            item_ids = itemIDs,
            item_locations = itemLocations,
            ignored_slots = ignoredSlots,
            item_level = CaptureEquipmentSetItemLevels(itemIDs, itemLocations, ignoredSlots),
        })
    end

    return sets
end

local function CaptureCharacter(reason)
    local db = EnsureDB()
    local characterName, realmName = UnitFullName("player")
    realmName = realmName or GetRealmName()
    local className, classFile = UnitClass("player")
    local specIndex = GetSpecialization()
    local specID, specName

    if specIndex then
        specID, specName = GetSpecializationInfo(specIndex)
    end

    if not specID or specID == 0 then
        return false
    end

    local captureKey = string.format("%s:%s:%d:%s", realmName or "", characterName or "", specID, reason or "")
    local now = type(GetTime) == "function" and GetTime() or 0
    if captureKey == lastCaptureKey and now - lastCaptureTime < DUPLICATE_CAPTURE_WINDOW_SECONDS then
        return true
    end

    local realmBucket = db.characters[realmName] or {}
    db.characters[realmName] = realmBucket

    local characterBucket = realmBucket[characterName] or {}
    realmBucket[characterName] = characterBucket
    characterBucket.equipment_sets = CaptureEquipmentSets()

    local specKey = tostring(specID or 0)
    characterBucket[specKey] = {
        captured_at = date("!%Y-%m-%dT%H:%M:%SZ"),
        character = characterName,
        realm = realmName,
        class = className,
        class_file = classFile,
        spec_id = specID,
        spec_name = specName,
        item_level = CaptureItemLevel(),
        click_bindings = CaptureClickBindings(),
        key_bindings = CaptureKeyBindings(),
        action_bars = CaptureActionBars(),
    }

    lastCaptureKey = captureKey
    lastCaptureTime = now

    print(string.format(
        "%s: captured %s - %s (%s, specID %d)%s.",
        ADDON_NAME,
        characterName,
        realmName,
        specName or "no spec",
        specID,
        reason and (" at " .. reason) or ""
    ))
    return true
end

local function ScheduleCapture(reason, delaySeconds, attempt)
    attempt = attempt or 1

    local function run()
        local captured = CaptureCharacter(reason)
        if captured or attempt >= MAX_SPEC_CAPTURE_ATTEMPTS then
            if not captured then
                print(string.format("%s: skipped capture at %s because active specialization was unavailable.", ADDON_NAME, reason))
            end
            return
        end

        -- The player/spec APIs can be unavailable for a moment during login,
        -- entering world, or rapid spec swaps. Retry instead of saving a fake
        -- spec_id 0 bucket.
        if C_Timer and C_Timer.After then
            C_Timer.After(SPEC_RETRY_DELAY_SECONDS, function()
                ScheduleCapture(reason, 0, attempt + 1)
            end)
        else
            print(string.format("%s: skipped capture retry at %s because timers were unavailable.", ADDON_NAME, reason))
        end
    end

    if C_Timer and C_Timer.After and delaySeconds and delaySeconds > 0 then
        C_Timer.After(delaySeconds, run)
    else
        run()
    end
end

SLASH_WOWPROFILECOLLECTOR1 = "/wowprofile"
SlashCmdList.WOWPROFILECOLLECTOR = function(message)
    message = (message or ""):lower():match("^%s*(.-)%s*$")
    if message == "capture" or message == "" then
        ScheduleCapture("manual request", 0)
    else
        print("WowProfileCollector commands: /wowprofile capture")
    end
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("PLAYER_LOGOUT")
frame:RegisterEvent("PLAYER_SPECIALIZATION_CHANGED")
frame:RegisterEvent("ACTIVE_PLAYER_SPECIALIZATION_CHANGED")
frame:RegisterEvent("EQUIPMENT_SWAP_FINISHED")
frame:RegisterEvent("EQUIPMENT_SETS_CHANGED")
frame:SetScript("OnEvent", function(_, event)
    EnsureDB()
    if event == "PLAYER_ENTERING_WORLD" then
        ScheduleCapture("login", LOGIN_CAPTURE_DELAY_SECONDS)
    elseif event == "PLAYER_LOGOUT" then
        CaptureCharacter("logout")
    elseif event == "PLAYER_SPECIALIZATION_CHANGED" or event == "ACTIVE_PLAYER_SPECIALIZATION_CHANGED" then
        ScheduleCapture("specialization change", SPEC_CAPTURE_DELAY_SECONDS)
    elseif event == "EQUIPMENT_SWAP_FINISHED" then
        ScheduleCapture("equipment swap finished", EQUIPMENT_CAPTURE_DELAY_SECONDS)
    elseif event == "EQUIPMENT_SETS_CHANGED" then
        ScheduleCapture("equipment sets changed", EQUIPMENT_SETS_CHANGED_DELAY_SECONDS)
    end
end)
