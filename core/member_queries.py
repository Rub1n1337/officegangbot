"""Member search + profile assembly for the dashboard, extracted from the RPC
handler so the filtering/shaping can be unit-tested without a live guild."""


def search_guild_members(guild, query: str, limit: int = 25) -> dict:
    """Up to `limit` non-bot members matching `query` (name / display name / id
    prefix), sorted by display name."""
    q = str(query or "").strip().lower()
    members = [m for m in guild.members if not m.bot]
    if q:
        members = [
            m
            for m in members
            if q in m.name.lower() or q in m.display_name.lower() or str(m.id).startswith(q)
        ]
    members.sort(key=lambda m: m.display_name.lower())
    return {
        "members": [
            {
                "id": str(m.id),
                "name": m.name,
                "displayName": m.display_name,
                "avatar": str(m.display_avatar.url),
            }
            for m in members[:limit]
        ]
    }


async def build_member_profile(guild, db, guild_id: int, user_id: int) -> dict:
    """A member's dashboard profile: level/XP, warnings, moderator notes,
    active AutoMod strikes and recent moderation cases — the full punitive
    history in one place — plus roles + join date when they're still in the
    server. Falls back to the stored display name for members who've left."""
    member = guild.get_member(user_id) if guild else None
    xp = await db.get_user_xp(guild_id, user_id)
    warnings = await db.get_warnings(guild_id, user_id)
    notes = await db.get_mod_notes(guild_id, user_id)
    strikes = await db.count_active_strikes_for(guild_id, user_id)
    cases = await db.get_mod_cases(guild_id, target_id=user_id, limit=10)
    result = {
        "id": str(user_id),
        "level": xp.get("level", 0),
        "xp": xp.get("xp", 0),
        "activeStrikes": int(strikes),
        "warnings": [
            {
                "id": w["id"],
                "reason": w["reason"],
                "moderatorName": w["moderator_name"],
                "createdAt": w["created_at"].isoformat() if w["created_at"] else None,
            }
            for w in warnings
        ],
        "notes": [
            {
                "id": n["id"],
                "note": n["note"],
                "authorName": n["author_name"],
                "createdAt": n["created_at"].isoformat() if n["created_at"] else None,
            }
            for n in notes
        ],
        "cases": [
            {
                "caseNumber": c["case_number"],
                "action": c["action"],
                "moderatorName": c["moderator_name"],
                "reason": c["reason"],
                "createdAt": c["created_at"].isoformat() if c["created_at"] else None,
            }
            for c in cases
        ],
    }
    if member:
        result.update({
            "name": member.name,
            "displayName": member.display_name,
            "avatar": str(member.display_avatar.url),
            "joinedAt": member.joined_at.isoformat() if member.joined_at else None,
            "inServer": True,
            "roles": [
                {"id": str(r.id), "name": r.name, "color": r.color.value}
                for r in reversed(member.roles)
                if not r.is_default()
            ],
        })
    else:
        name = xp.get("display_name") or f"User {user_id}"
        result.update({
            "name": name,
            "displayName": name,
            "avatar": None,
            "joinedAt": None,
            "inServer": False,
            "roles": [],
        })
    return result
