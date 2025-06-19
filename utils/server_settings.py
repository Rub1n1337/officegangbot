import json
import os

class ServerSettings:
    def __init__(self, filename="server_setups.json"):
        self.filename = filename
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.filename):
            return {}
        with open(self.filename, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.filename, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_settings(self, guild_id):
        return self.data.get(str(guild_id), {})

    def set_settings(self, guild_id, settings):
        self.data[str(guild_id)] = settings
        self.save()

    def remove_settings(self, guild_id):
        if str(guild_id) in self.data:
            del self.data[str(guild_id)]
            self.save()

    def is_setup_complete(self, guild_id):
        settings = self.get_settings(guild_id)
        return settings.get('setup_complete', False)

    def set_setup_complete(self, guild_id):
        settings = self.get_settings(guild_id)
        settings['setup_complete'] = True
        self.set_settings(guild_id, settings)
