import json

class KSSMconfig:
	_instance = None
	
	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
			cls._instance.load_config()
		return cls._instance
	
	def load_config(self, config = 'kssm.json'):
		with open(config, 'r') as config_file:
			config_data = json.load(config_file)
			for key, value in config_data.items():
				setattr(self, key, value)
	
	def __getattr__(self, name):
		raise AttributeError(f"Configuration '{name}' not found")
