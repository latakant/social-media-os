from memory.store import get_post_records

records = get_post_records()
print(f"{len(records)} record(s) in DB\n")
for r in records:
    print(f"post_id:  {r['post_id']}")
    print(f"platform: {r['platform']}")
    print(f"posted:   {r['posted_at']}")
    print(f"words:    {len(r['approved_content'].split())}")
    print(f"engaged:  {r['engagement_result'] or 'not collected yet'}")
    print()
