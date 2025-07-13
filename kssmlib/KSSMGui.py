import wx
import json
from gui.KSSMBaseGUI import KSSMBaseFrame, KSSMBaseMapEditFrame

class KSSMMainFrame(KSSMBaseFrame):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
	
	def CloseFrame(self, event): 
		self.Close()
	
	def OpenMapEditor(self, event):
		mapframe = KSSMMapEditFrame(None, wx.ID_ANY, "")
		mapframe.Show()
		mapframe.Maximize(True)

class KSSMMapEditFrame(KSSMBaseMapEditFrame):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
		self.nodes = None
	
	def OpenDialogJSONNodes(self, event):
		with wx.FileDialog(self, "Open map file", wildcard="json files (*.json)|*.json", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
			if fileDialog.ShowModal() == wx.ID_CANCEL:
				return
			pathname = fileDialog.GetPath()
			try:
				with open(pathname, 'r') as file:
					self.nodes = json.load(file)
					self.loadNodesFromList()
			except IOError:
				wx.LogError("Cannot open file '%s'." % newfile)
	
	def resetNodes(self):
		self.node_choice.Clear()
		self.x_pos_value.Clear()
		self.y_pos_value.Clear()
		self.z_pos_value.Clear()
		self.node_id.Clear()
		self.tx_power.SetValue(0)
		self.frequency.SetValue(869525000)
		
	
	def loadNodesFromList(self):
		if self.nodes is None:
			return
		self.resetNodes()
		for n in self.nodes:
			self.node_choice.Append(n["node_id"])

class KSSMGUI(wx.App):
	def OnInit(self):
		self.frame = KSSMMainFrame(None, wx.ID_ANY, "")
		self.SetTopWindow(self.frame)
		self.frame.Show()
		self.frame.Maximize(True)
		return True
