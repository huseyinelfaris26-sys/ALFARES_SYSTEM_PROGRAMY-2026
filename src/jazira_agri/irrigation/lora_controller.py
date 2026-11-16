"""التحكم بصمامات الري عبر لورا"""
class LoraValveController:
    def __init__(self, node_address):
        self.addr = node_address
        self.status = False

    def open_valve(self):
        self.status = True
        return f"صمام {self.addr}: مفتوح ✅"

    def close_valve(self):
        self.status = False
        return f"صمام {self.addr}: مغلق ✅"
