import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class FunctionPlotter:
    def __init__(self, master):
        self.master = master
        master.title("实时函数可视化 v1.0")
        
        # 初始化参数
        self.params = {
            '振幅': 1.0,
            '频率': 1.0,
            '相位': 0.0,
            '偏移': 0.0,
            '噪声': 0.1
        }
        
        # 创建界面组件
        self.create_widgets()
        self.update_plot()
    
    def create_widgets(self):
        # 创建Matplotlib画布
        fig = plt.Figure(figsize=(6, 4))
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, master=self.master)
        self.canvas.get_tk_widget().grid(row=0, column=1, rowspan=5)
        
        # 参数输入区域
        self.entries = {}
        for i, (name, value) in enumerate(self.params.items()):
            ttk.Label(self.master, text=name).grid(row=i, column=0, sticky='w')
            self.entries[name] = ttk.Entry(self.master)
            self.entries[name].insert(0, str(value))
            self.entries[name].grid(row=i, column=2, padx=5, pady=2)
        
        # 控制按钮
        ttk.Button(self.master, text="更新参数", 
                 command=self.update_params).grid(row=5, column=2, pady=10)
    
    def update_params(self):
        """更新参数值"""
        for name, entry in self.entries.items():
            try:
                self.params[name] = float(entry.get())
            except ValueError:
                print(f"无效输入: {name}")
        self.update_plot()
    
    def generate_data(self):
        """生成函数数据"""
        x = np.linspace(0, 4*np.pi, 1000)
        y = (self.params['振幅'] * np.sin(self.params['频率'] * x + self.params['相位']) 
             + self.params['偏移']
             + np.random.normal(0, self.params['噪声'], x.shape))
        return x, y
    
    def update_plot(self):
        """更新图表"""
        x, y = self.generate_data()
        self.ax.clear()
        self.ax.plot(x, y, 'b-', lw=1)
        self.ax.set_title("实时函数可视化")
        self.ax.grid(True)
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = FunctionPlotter(root)
    root.mainloop()