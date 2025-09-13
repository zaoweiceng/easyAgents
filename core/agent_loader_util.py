import importlib.util
import os
import sys

def filename_to_classname(filename):
    # 移除文件扩展名（如果存在）
    if filename.endswith('.py'):
        filename = filename[:-3]
    
    # 按下滑线分割文件名
    parts = filename.split('_')
    
    # 将每个部分的首字母大写，然后连接起来
    class_name = ''.join(part.capitalize() for part in parts if part)
    
    return class_name

def load_class_from_file(file_path, class_name):
    # 将文件路径转化为绝对路径
    file_path = os.path.abspath(file_path)
    # 提取模块名（不含路径和扩展名）
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # 创建模块规范
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Could not load spec from file {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    
    # 执行模块
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Error while executing module {module_name}: {e}")
    
    # 获取类
    if hasattr(module, class_name):
        return getattr(module, class_name)
    else:
        raise AttributeError(f"Module {module_name} does not have class {class_name}")