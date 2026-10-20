import os, sys, traceback
import cadquery as cq
import parts as P
import parts_modules as M
import parts_panel as F
import parts_dock as D
PARTS = {
 "P01_Sharp_LJ64K052_EL": P.lj64k052,
 "P02_Tang_Primer_20K_Core": P.tang20k_core,
 "P03_Tang_Primer_20K_Dock": P.tang20k_dock,
 "P04_OrangePi_4": P.orangepi4,
 "P05_IN-14_Nixie": P.in14,
 "P06_IV-18_VFD": P.iv18,
 "P09_K155ID1_DIP16": P.dip16,
 "P10_MeanWell_LRS-200-24": M.lrs200_24,
 "P11_MeanWell_NID100-05": P.nid100_05,
 "P12_MeanWell_NID100-12": P.nid100_05,
 "P13_NCH6100HV": P.nch6100hv,
 "P16_24V_Power_Board": P.power_board,
 "P17_2020_Profile_L100_sample": lambda: P.profile_2020(100),
 "P18_2020_Corner_Bracket": P.corner_bracket_2020,
 "P19_TNut_M4_Slot6": P.tnut_m4_slot6,
 "P20_Standoff_M3x10": lambda: P.standoff_m3(10),
 "P21_EC11_Encoder_with_Knob": P.ec11,
 "P23_SMA_Bulkhead": P.sma_bulkhead,
 "P24_Fan_60x15": lambda: P.fan(60,15),
 "P25_Fan_40x10": lambda: P.fan(40,10),
 "P26_EL_Bracket": P.el_bracket,
 "P27_IN-14_Socket_PCB": P.in14_socket_pcb,
 "P28_IV-18_PCB": P.iv18_pcb,
 "P29_Tube_Driver_Board": P.tube_driver_board,
 "P31_J305_Geiger": M.j305,
 "P32_ESP32-S3_DEV-KIT_Waveshare": M.esp32s3_dev_kit,
 "P33_RaspberryPi_Pico": M.rpi_pico,
 "P34_XL6009_Module": M.xl6009_module,
 "P35_MAX6921_SOIC28": M.max6921_soic28,
 "P36_Electret_Mic_CZN-15E": M.electret_mic_czn15e,
 "P37_USB-A_Socket": M.usb_a_socket,
 "P38_Geiger_Board": M.geiger_board,
 "P39_Square_Lamp_Button_16": F.square_lamp_button,
 "P40_Toggle_Switch_Guarded": F.toggle_guarded,
 "P41_Indicator_Lamp_8mm": F.indicator_lamp,
 "P42_Rotary_Selector_with_Knob": F.rotary_selector,
 "P43_Panel_Meter_85C1": F.panel_meter,
 "P44_Speaker_40mm": F.speaker_40,
 "P46_IEC_C14_Inlet": F.iec_c14_inlet,
 "P47_X1_Tablet_Keyboard": M.x1_tablet_keyboard,
 "P48_Fader_60mm": F.fader_60,
 "P49_LA16_Rect_Lamp_Button_24x18": F.rect_lamp_button,
 "P50_6E2_Indicator_Tube": M.tube_6e2,
 "P51_Noval_Socket_9pin": M.noval_socket,
 "P52_USB_Panel_Extension": F.usb_panel_ext,
 "P54_DS3231_Module": M.ds3231_module,
 "P55_Geiger_Clip_Board": M.geiger_clip_board,
 "P53_Keyboard_Dock": D.keyboard_dock,
}
if __name__ == "__main__":
    os.makedirs("step/parts", exist_ok=True)
    ok = {}
    only = sys.argv[1:]                  # 可选：只导出编号以这些前缀开头的零件，如 P31 P32
    for name, fn in PARTS.items():
        if only and not name.startswith(tuple(only)):
            continue
        try:
            s = fn()
            sol = s.val()
            bb = sol.BoundingBox()
            cq.exporters.export(s, f"step/parts/{name}.step")
            ok[name] = s
            print(f"OK  {name:34s} {bb.xlen:7.1f} x {bb.ylen:7.1f} x {bb.zlen:7.1f}  solids={len(s.solids().vals())}"
                  + ("" if s.solids().vals() else "  (曲面模型)"))
        except Exception as e:
            print("ERR", name, repr(e)); traceback.print_exc(limit=1)
