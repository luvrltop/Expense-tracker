import ttkbootstrap as tb
import tkinter
import os


main_window = tb.Window(title ="Expense tracker 1.0", themename="darksapphire")

main_window.minsize(1500, 1200)
main_window.resizable(True, True)

main_frame = tb.Frame(main_window, borderwidth=10, relief = "groove", height= 700, width=1000)

main_frame.pack()
header = tb.Label(main_frame, text="Expense tracker", font="Arial, 28", padding=10, background = "gray", foreground="black", relief="groove")
header.pack(pady=(70,0))
main_window.mainloop()