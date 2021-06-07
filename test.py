import tkinter as tk
from tkinter import ttk

root = tk.Tk()
style = ttk.Style()
style.theme_create( "MyStyle", parent="alt", settings={
        "TNotebook": {"configure": {"tabmargins": [2, 5, 2, 0] } },
        "TNotebook.Tab": {"configure": {"padding": [100, 100] },}})

style.theme_use("MyStyle")

a_notebook = ttk.Notebook(root, width=200, height=200)
a_tab = ttk.Frame(a_notebook)
a_notebook.add(a_tab, text = 'This is the first tab')
another_tab = ttk.Frame(a_notebook)
a_notebook.add(another_tab, text = 'This is another tab')
a_notebook.pack(expand=True, fill=tk.BOTH)

tk.Button(root, text='Some Text!').pack(fill=tk.X)

root.mainloop()