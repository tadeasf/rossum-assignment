WHAT HAS CHANGED:
flow:
- when running function trigger (which would be usually done via document upload I imagine rather than manual hook) we read config.yml (see in /src/lib/trigger/config.yml)
- config.yml contains mapping and configuration
- trigger.py uses it to construct pycurl call which contains payload.settings with annotation_id and configuration details
- the rossum_hook.py itself - according to feedback i reworked xml handling as well as the rossum api response
   - we are getting basic python types and then constructing the xml via ET

