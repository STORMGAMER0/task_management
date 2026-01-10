# In Python shell
try:
    from tasks.export import export_tasks_csv, export_tasks_pdf
    print("✅ Import successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()