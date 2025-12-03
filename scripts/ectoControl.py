from argparse import ArgumentParser
from pymodbus.client import ModbusTcpClient
import struct

class EctoControlClient:
    def __init__(self):
        self._client = ModbusTcpClient(host='192.168.2.131', port=8899)
        self._device_id = 0xe

    def connect(self):
        self._client.connect()

    def close(self):
        self._client.close()

    def read_value(self, address, count):
        if count == 1:
            pdu = self._client.read_holding_registers(address=address, count=1, device_id=self._device_id)
            return pdu.registers[0]
        elif count == 2:
            pdu = self._client.read_holding_registers(address=address, count=2, device_id=self._device_id)
            return int.from_bytes(struct.pack(">HH", pdu.registers[0] & 0xFFFF, pdu.registers[1] & 0xFFFF), byteorder="big")
        elif count == 3:
            pdu = self._client.read_holding_registers(address=address, count=3, device_id=self._device_id)
            return int.from_bytes(struct.pack(">HHH", pdu.registers[0] & 0xFFFF, pdu.registers[1] & 0xFFFF, pdu.registers[2] & 0xFFFF), byteorder="big")
        else:
            raise Exception("Not supported")
        
    def write_value(self, address, value):
        self._client.write_registers(address=address, values=[value], device_id=self._device_id)

client = EctoControlClient()

class CurrentTemperatureParameter:
    def read(self):
        self._t = client.read_value(address=0x18, count=1) * 0.1
    def __str__(self):
        return "Текущая температура теплоносителя: " + str(self._t) + " °C"

class UptimeParameter:
    def read(self):
        self._time = client.read_value(address=0x12, count=2)
    def __str__(self):
        return "Время работы: " + str(self._time) + " сек."

class CurrentPressureParameter:
    def read(self):
        self._pressure = client.read_value(address=0x1a, count=1) * 0.1
    def __str__(self):
        return "Текущее давление в контуре: " + str(self._pressure) + " бар"

class CurrentStateParameter:
    def read(self):
        self._state = bool(client.read_value(address=0x1d, count=1) & 0x2)
    def __str__(self):
        return "Текущее состояние отопления: " + str(self._state)
    
class TemperatureControlParameter:
    def read(self):
        self._temperature = client.read_value(address=0x31, count=1) * 0.1
    def write(self, value):
        self._temperature = value
        value = value * 10
        client.write_value(address=0x31, value=value)
        print(str(self))
    def __str__(self):
        return "Установка теплоносителя: " + str(self._temperature) + " °C"

class TemperatureEmergencyControlParameter:
    def read(self):
        self._temperature = client.read_value(address=0x32, count=1) * 0.1
    def write(self, value):
        self._temperature = value
        value = value * 10
        client.write_value(address=0x32, value=value)
        print(str(self))
    def __str__(self):
        return "Установка теплоносителя (аварийно): " + str(self._temperature) + " °C"
    
class ModulationControlParameter:
    def read(self):
        self._modulation = client.read_value(address=0x38, count=1)
    def write(self, value):
        self._modulation = value
        client.write_value(address=0x38, value=value)
        print(str(self))
    def __str__(self):
        return "Модуляция котла: " + str(self._modulation) + "%"
    
class StateControlParameter:
    def read(self):
        self._state = bool(client.read_value(address=0x39, count=1) & 0x1)
    def write(self, value):
        self._state = bool(value)
        oldValue = client.read_value(address=0x39, count=1)

        if value:
            client.write_value(address=0x39, value=oldValue | 1)
        else:
            client.write_value(address=0x39, value=oldValue & (~1))

        print(str(self))
    def __str__(self):
        return "Режим контура отопления: " + str(self._state)
    
class ResetControlParameter:
    def read(self):
        pass
    def execute(self):
        client.write_value(address=0x80, value=2)
        print("Адаптер перезагружен")
    def __str__(self):
        pass

class InfoControlParameter:
    def read(self):
        self._state = client.read_value(address=0x03, count=1)
        pass
    def execute(self):
        pass
    def __str__(self):
        addr = (self._state & 0xFF)
        type = ((self._state >> 8) & 0xFF)
        chn_cnt = ((self._state >> 16) & 0xFF)
        return f"Информация: {hex(addr)} (addr), {hex(type)} (type), {hex(chn_cnt)} (chn_cnt)"
    
class ConnectionControlParameter:
    def read(self):
        self._state = client.read_value(address=0x30, count=1)
    def write(self, value):
        pass
    def __str__(self):
        return "Подключение адаптера к котлу: " + str(self._state)

def read_and_print_parameters(*parameters):
    for x in parameters:
        x.read()
    print_parameters(*parameters)

def print_parameters(*parameters):
    print("Данные сенсоров:")
    print("\n".join(map(lambda a: " " + str(a), parameters)))

def main():
    client.connect()

    parser = ArgumentParser()

    parser.add_argument("--read-all", help="Считать все значения сенсоров", action='store_true')

    parser.add_argument("--set-temperature", type=int, help="Установка теплоносителя (и аварийно)")
    parser.add_argument("--set-modulation", type=int, help="Установить модуляцию")
    parser.add_argument("--set-state", type=int, help="Режим контура отопления")
    parser.add_argument("--reset-adapter", action="store_true", help="Перзапустить адаптер")

    args = parser.parse_args()

    if (args.read_all):
        curentTemperature = CurrentTemperatureParameter()
        uptime = UptimeParameter()
        currentPressure = CurrentPressureParameter()
        state = CurrentStateParameter()
        temperatureControl = TemperatureControlParameter()
        temperatureEmergencyControl = TemperatureEmergencyControlParameter()
        modulation = ModulationControlParameter()
        stateControl = StateControlParameter()
        info = InfoControlParameter()
        connection = ConnectionControlParameter()

        read_and_print_parameters(
            curentTemperature, 
            uptime, 
            currentPressure, 
            state,
            temperatureControl,
            temperatureEmergencyControl,
            modulation,
            stateControl,
            info,
            connection
        )
    elif (args.set_temperature or args.set_temperature == 0):
        temperature1 = TemperatureControlParameter()
        temperature1.write(args.set_temperature)

        temperature2 = TemperatureEmergencyControlParameter()
        temperature2.write(args.set_temperature)
    elif (args.set_modulation or args.set_modulation == 0):
        modulation = ModulationControlParameter()
        modulation.write(args.set_modulation)
    elif (args.set_state or args.set_state == 0):
        state = StateControlParameter()
        state.write(args.set_state)
    elif (args.reset_adapter):
        reset = ResetControlParameter()
        reset.execute()
    else:
        parser.print_help()

    client.close()

if __name__ == "__main__":
    main()
