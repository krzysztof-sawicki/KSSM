import math

class MeshPropagation:
	"""
	model (str): name of the model, possible values are:
		FSPL - free space path loss,
		OpenTerrain - Okumura-Hata model for open terrain,
		Suburban - Okumura-Hata model for suburban areas,
		City - Okumura-Hata model for large cities
	"""
	def __init__(self, model='FSPL'):
		self.model = model
		self._path_loss_cache = {}
		self._distance_cache = {}

	def calculate_distance(self, node_tx, node_rx):
		cache_key = (node_tx.node_id, node_rx.node_id)
		if cache_key in self._distance_cache:
			return self._distance_cache[cache_key]
		pos_a = node_tx.position
		pos_b = node_rx.position
		distance = math.sqrt((pos_b[0] - pos_a[0])**2 + (pos_b[1] - pos_a[1])**2 + (pos_b[2] - pos_a[2])**2)
		self._distance_cache[cache_key] = distance
		return distance

	def calculate_path_loss(self, node_tx, node_rx):
		cache_key = (node_tx.node_id, node_rx.node_id)
		if cache_key in self._path_loss_cache:
			return self._path_loss_cache[cache_key]
		distance = self.calculate_distance(node_tx, node_rx)

		if distance == 0:
			return 0.0

		path_loss = None
		frequency = node_tx.frequency
		
		"""
		The Okumura-Hata model is specifically designed for mobile devices and elevated base stations. 
		The height of the transmitting antenna in the model has a greater impact than the height of 
		the receiving antenna. In the context of a mesh network, such a comparison is not suitable, 
		so the average attenuation in both directions is calculated.
		"""
		path_loss = -1
		if self.model == 'OpenTerrain':
			path_loss1 = self.model_okumura_hata_open(distance, frequency, node_tx.position[2], node_rx.position[2])
			path_loss2 = self.model_okumura_hata_open(distance, frequency, node_rx.position[2], node_tx.position[2])
		elif self.model == 'Suburban':
			path_loss1 = self.model_okumura_hata_suburban(distance, frequency, node_tx.position[2], node_rx.position[2])
			path_loss2 = self.model_okumura_hata_suburban(distance, frequency, node_rx.position[2], node_tx.position[2])
		elif self.model == 'City':
			path_loss1 = self.model_okumura_hata_large_city(distance, frequency, node_tx.position[2], node_rx.position[2])
			path_loss2 = self.model_okumura_hata_large_city(distance, frequency, node_rx.position[2], node_tx.position[2])
		else: #every other option is FSPL
			path_loss = self.model_fspl(distance, frequency, node_tx.position[2], node_rx.position[2])
		if path_loss == -1:
			path_loss = (path_loss1 + path_loss2) / 2.0

		if path_loss is not None:
			self._path_loss_cache[cache_key] = path_loss
		return path_loss

	def model_fspl(self, d, f, h_tx, h_rx):
		d_km = d / 1000.0
		f_ghz = f / 1000000000.0
		if d_km <= 0 or f_ghz <= 0:
			return float('inf')
		fspl_db = 32.44 + 20 * math.log10(d_km) + 20 * math.log10(f_ghz)
		return fspl_db

	def model_okumura_hata_open(self, d, f, h_tx, h_rx):
		"""
		Okumura-Hata model for open terrain
		"""
		d_km = d / 1000.0
		f_mhz = f / 1000000.0

		c_h = (1.1 * math.log10(f_mhz) - 0.7) * h_rx - (1.56 * math.log10(f_mhz) - 0.8)
		l_u = (69.55 + 26.16 * math.log10(f_mhz) - 13.82 * math.log10(h_tx) - c_h + (44.9 - 6.55 * math.log10(h_tx)) * math.log10(d_km))
		l_open = l_u - 4.78 * (math.log10(f_mhz) ** 2) + 18.33 * math.log10(f_mhz) - 40.94

		return l_open

	def model_okumura_hata_suburban(self, d, f, h_tx, h_rx):
		"""
		Okumura-Hata model for suburban areas
		"""
		d_km = d / 1000.0
		f_mhz = f / 1000000.0

		c_h = (1.1 * math.log10(f_mhz) - 0.7) * h_rx - (1.56 * math.log10(f_mhz) - 0.8)
		l_u = (69.55 + 26.16 * math.log10(f_mhz) - 13.82 * math.log10(h_tx) - c_h + (44.9 - 6.55 * math.log10(h_tx)) * math.log10(d_km))
		l_suburban = l_u - 2 * ((math.log10(f_mhz / 28.0)) ** 2) - 5.4

		return l_suburban

	def model_okumura_hata_large_city(self, d, f, h_tx, h_rx):
		"""
		Okumura-Hata model for large cities
		"""
		d_km = d / 1000.0
		f_mhz = f / 1000000.0

		if f_mhz <= 200:
			c_h = 8.29 * (math.log10(1.54 * h_rx) ** 2) - 1.1
		elif f_mhz >= 400:
			c_h = 3.2 * (math.log10(11.75 * h_rx) ** 2) - 4.97
		else:
			raise ValueError("This model can't be used for 200 < f < 400 MHz.")
		l_large_city = (69.55 + 26.16 * math.log10(f_mhz) - 13.82 * math.log10(h_tx) - c_h + (44.9 - 6.55 * math.log10(h_tx)) * math.log10(d_km))

		return l_large_city
