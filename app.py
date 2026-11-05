import sys
"""MC Resource Table: Minecraft Java resource pack editor (experimental)."""
import io
import tempfile
import time
import shutil
import json
import os
import math
from pathlib import Path
import re
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageDraw

TRANSLATIONS = {'한국어': {'Find Minecraft': '마인크래프트 찾기', 'Load JAR / ZIP': 'JAR / ZIP 열기', 'Load assets folder': '에셋 폴더 열기', 'Import PNG': 'PNG 가져오기', 'Other Assets': '기타 리소스', 'Open Project': '프로젝트 열기', 'Save Project': '프로젝트 저장', 'Validate Pack': '팩 검사', 'Export Pack ZIP': '팩 ZIP 내보내기', 'Install ZIP': 'ZIP 설치', 'File & Tools': '파일 및 도구', 'Help': '도움말', 'Start Beginner Tutorial': '초보자 튜토리얼', 'Quick Reference': '빠른 사용법', 'RESOURCE GALLERY': '리소스 갤러리', 'New texture': '새 텍스처', 'Open editor': '편집기 열기', 'Search': '검색', 'Category': '분류', '  Click an image to edit': '  이미지를 클릭하면 편집합니다', 'Fullscreen 3D': '3D 전체화면', 'Back to gallery': '갤러리로', 'Pencil': '연필', 'Eraser': '지우개', 'Fill': '채우기', 'Select': '선택', 'Move': '이동', 'Eyedropper': '스포이트', 'Reset view': '시점 초기화', '3D Fullscreen':'⛶ 3D 전체화면'}, '日本語': {'Find Minecraft': 'Minecraftを探す', 'Load JAR / ZIP': 'JAR / ZIPを開く', 'Load assets folder': '素材フォルダ', 'Import PNG': 'PNGを読み込む', 'Other Assets': 'その他の素材', 'Open Project': 'プロジェクトを開く', 'Save Project': 'プロジェクトを保存', 'Validate Pack': 'パックを検証', 'Export Pack ZIP': 'ZIPを書き出す', 'Install ZIP': 'ZIPを配置', 'File & Tools': 'ファイルとツール', 'Help': 'ヘルプ', 'Start Beginner Tutorial': '初心者ガイド', 'Quick Reference': 'クイックガイド', 'RESOURCE GALLERY': 'リソース一覧', 'New texture': '新しいテクスチャ', 'Open editor': '編集画面', 'Search': '検索', 'Category': 'カテゴリ', '  Click an image to edit': '  画像をクリックして編集', '3D Fullscreen':'⛶ 3D全画面'}, 'Español': {'Find Minecraft': 'Buscar Minecraft', 'Load JAR / ZIP': 'Abrir JAR / ZIP', 'Load assets folder': 'Abrir carpeta', 'Import PNG': 'Importar PNG', 'Other Assets': 'Otros recursos', 'Open Project': 'Abrir proyecto', 'Save Project': 'Guardar proyecto', 'Validate Pack': 'Validar paquete', 'Export Pack ZIP': 'Exportar ZIP', 'Install ZIP': 'Instalar ZIP', 'File & Tools': 'Archivo y herramientas', 'Help': 'Ayuda', 'Start Beginner Tutorial': 'Tutorial inicial', 'Quick Reference': 'Guía rápida', 'RESOURCE GALLERY': 'GALERÍA DE RECURSOS', 'New texture': 'Nueva textura', 'Open editor': 'Abrir editor', 'Search': 'Buscar', 'Category': 'Categoría', '  Click an image to edit': '  Haz clic para editar', '3D Fullscreen':'⛶ 3D pantalla completa'}}

PREFIX = 'assets/minecraft/textures/'
VALID = re.compile(r'^(block|item|gui|entity|particle|environment|font|colormap|misc|effect|painting|map|mob_effect|models|atlas)/[a-z0-9_./-]+$')

class Studio:
    def __init__(self, root):
        self.root = root
        self.settings_path=Path.home()/'.mc_resource_table'/'settings.json'
        try:
            saved=json.loads(self.settings_path.read_text(encoding='utf-8'))
            language=saved.get('language','English')
        except (OSError,ValueError,TypeError):
            saved={}
            language='English'
        self.settings=saved if isinstance(saved,dict) else {}
        self.language=tk.StringVar(value=language if language in ('English',*TRANSLATIONS) else 'English')
        root.title('MC Resource Table 13.4 — Entity Model Import')
        root.geometry('1520x940')
        root.minsize(920, 650)
        self.other_assets = {}  # Original and edited non-PNG assets.
        self.other_base = {}  # Original non-PNG assets for model lookup.
        self.modified_other = set()  # Export only intentionally modified non-PNG assets.
        self.base = {}  # Original vanilla PNG bytes loaded from a local client jar/assets ZIP.
        self.edits = {}
        self.names = set(['block/stone', 'block/dirt', 'block/grass_block_top', 'block/oak_planks', 'item/diamond_sword', 'item/apple'])
        self.current = 'block/stone'
        self.image = Image.new('RGBA', (16,16), (0,0,0,0))
        self.layer_docs = {}
        self.layers = []
        self.active_layer = 0
        self.history = []
        self.redo_stack = []
        self.color = (38, 174, 238, 255)
        self.tool = tk.StringVar(value='Pencil')
        self.category = tk.StringVar(value='All')
        self.search = tk.StringVar()
        self.pack_name = tk.StringVar(value='My MC Resource Pack')
        self.format = tk.StringVar(value='15')
        self.minecraft_version = tk.StringVar(value='Unknown')
        self.project_file = None
        self.autosave_path = Path.home() / '.mc_resource_table' / 'recovery.prism'
        self.last_recovery_signature = None
        self.status = tk.StringVar(value='Only 6 examples are shown until you load Minecraft assets. Click Find installed Minecraft.')
        self.grid_on = tk.BooleanVar(value=True)
        self.selection = None
        self.anchor = None
        self.drag_origin = None
        self.drag_image = None
        self.preview_offset = (0,0)
        self.clipboard = None
        self.dirty = False
        self.zoom = 20
        self.photo = None
        self.configure_style()
        self.gallery_page=0
        self.preview_photo=None
        self.fullscreen_window=None
        self.fullscreen_canvas=None
        self.fullscreen_photo=None
        self.preview_pick=None
        self.preview_pick_size=0
        self.preview_pick_offset=(0,0)
        self.preview_job=None
        self.preview_interactive=False
        self.preview_face_signature=None
        self.entity_models={}  # keyed by texture path; user-imported model data
        self.preview_rotation=0
        self.view_yaw=0.65
        self.view_pitch=0.45
        self.view_zoom=1.0
        self.view_drag_start=None
        self.gallery_photos=[]
        self.gallery_page_size=48
        self.set_app_icon()
        self.create_ui()
        self.apply_language()
        self.open_path(self.current, initial=True)
        self.show_editor()
        self.root.after(60000,self.autosave_tick)
        self.root.after(700,self.offer_recovery)
        self.root.after(1500,self.offer_first_run_tutorial)
        self.root.after(250,self.restore_last_assets)
        root.bind('<Control-z>', lambda e: self.undo())
        root.bind('<F11>', lambda e: self.open_fullscreen_preview())
        root.bind('<Control-y>', lambda e: self.redo())
        root.bind('<Control-s>', lambda e: self.save())
        root.bind('<Control-c>', lambda e: self.copy_selection())
        root.bind('<Control-x>', lambda e: self.cut_selection())
        root.bind('<Control-v>', lambda e: self.paste_selection())
        root.bind('<Delete>', lambda e: self.delete_selection())

    def set_app_icon(self):
        try:
            path=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'mc_resource_table.png'
            self.app_icon=tk.PhotoImage(file=str(path))
            self.root.iconphoto(True,self.app_icon)
        except (tk.TclError,OSError):pass

    def tr(self, text):
        return TRANSLATIONS.get(self.language.get(),{}).get(text,text)

    def set_language(self,language):
        self.language.set(language)
        try:
            self.settings_path.parent.mkdir(parents=True,exist_ok=True)
            self.settings['language']=language
            self.write_settings()
        except OSError:pass
        self.apply_language()

    def write_settings(self):
        # Preserve language and asset path together; write atomically.
        self.settings_path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.settings_path.with_suffix('.tmp')
        try:
            temp.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,self.settings_path)
        finally:
            try:temp.unlink(missing_ok=True)
            except OSError:pass

    def remember_assets(self,kind,path):
        self.settings['last_assets']={'kind':kind,'path':str(Path(path).resolve())}
        try:self.write_settings()
        except OSError as exc:self.status.set('Assets loaded, but remembering location failed: '+str(exc))

    def restore_last_assets(self):
        info=self.settings.get('last_assets')
        if not isinstance(info,dict):return
        kind=info.get('kind');path=info.get('path')
        if kind not in ('jar','folder') or not isinstance(path,str):return
        if not Path(path).exists():
            self.status.set('Previous Minecraft assets not found. Use Find Minecraft to select them again.')
            return
        try:
            if kind=='jar':self.import_asset_zip(path,notify=False,remember=False)
            else:self.import_asset_folder(path,remember=False)
            self.status.set(f'Automatically restored {len(self.base):,} textures from {Path(path).name}.')
        except Exception as exc:
            self.status.set('Could not restore previous Minecraft assets: '+str(exc))

    def apply_language(self):
        # Update static widget captions without rebuilding the editor or losing edits.
        for widget,english in getattr(self,'translatable_widgets',[]):
            try:
                if widget.winfo_exists():widget.configure(text=self.tr(english))
            except tk.TclError:pass
        for menu,index,english in getattr(self,'translatable_menus',[]):
            try:menu.entryconfigure(index,label=self.tr(english))
            except tk.TclError:pass
        self.root.title('MC Resource Table 12.8 — '+self.language.get())
        self.status.set({
            '한국어':'언어가 한국어로 설정되었습니다. 마인크래프트 찾기를 눌러 시작하세요.',
            '日本語':'言語を日本語に変更しました。Minecraftを探すから始めてください。',
            'Español':'Idioma cambiado a español. Empieza con Buscar Minecraft.'
        }.get(self.language.get(),'Language set to English. Start with Find Minecraft.'))

    def register_translatable_widgets(self,widget):
        for child in widget.winfo_children():
            try:
                label=child.cget('text')
                if label and isinstance(label,str) and label in set(k for d in TRANSLATIONS.values() for k in d):
                    if not any(w is child for w,_ in self.translatable_widgets):
                        self.translatable_widgets.append((child,label))
            except (tk.TclError,AttributeError):pass
            self.register_translatable_widgets(child)

    def offer_first_run_tutorial(self):
        flag=Path.home()/'.mc_resource_table'/'tutorial_seen'
        if flag.exists():return
        try:
            flag.parent.mkdir(parents=True,exist_ok=True)
            flag.write_text('1',encoding='utf-8')
        except OSError:pass
        prompt= ('리소스팩 제작이 처음인가요?\\n\\n간단한 사용법 튜토리얼을 시작할까요?\\n도움말 메뉴에서 언제든 다시 열 수 있습니다.'
                 if self.language.get()=='한국어' else
                 'New to resource packs?\\n\\nWould you like a short guided tutorial?\\nYou can reopen it anytime from Help > Start Beginner Tutorial.')
        if messagebox.askyesno('MC Resource Table',prompt):
            self.show_tutorial()

    def show_quick_reference(self):
        if self.language.get()=='한국어':
            messagebox.showinfo('빠른 사용법',
                '1. 마인크래프트 찾기: 원본 게임 텍스처 불러오기\\n'
                '2. 검색 / 분류: 블록, 아이템, GUI 텍스처 찾기\\n'
                '3. 썸네일 클릭: 픽셀 편집기 열기\\n'
                '4. 연필 / 채우기 / 선택: 수정하기 (Ctrl+Z 실행 취소)\\n'
                '5. 3D 전체화면(F11): 회전, 확대, 면 클릭\\n'
                '6. 프로젝트 저장: 작업 저장\\n'
                '7. 팩 검사 후 ZIP 내보내기\\n'
                '8. ZIP 설치: Minecraft resourcepacks 폴더로 복사\\n\\n'
                'Minecraft Java 원본 파일은 직접 불러와야 합니다.')
            return
        messagebox.showinfo('Quick Reference',
            '1. Find Minecraft: load the original game textures.\\n'
            '2. Search / Category: locate a block, item or GUI texture.\\n'
            '3. Click a thumbnail to open the pixel editor.\\n'
            '4. Pencil / Fill / Select: edit the texture. Ctrl+Z undoes.\\n'
            '5. Fullscreen 3D (F11): orbit, zoom and click a block face.\\n'
            '6. Save Project: save editable work.\\n'
            '7. Validate Pack, then Export Pack ZIP.\\n'
            '8. Install ZIP: copy it to the Minecraft resourcepacks folder.\\n\\n'
            'Original Minecraft textures are NOT included. Load your own Java Edition assets.')

    def show_tutorial(self):
        if getattr(self,'tutorial_window',None) and self.tutorial_window.winfo_exists():
            self.tutorial_window.lift()
            return
        steps=[
            ('Welcome!',
             'This walkthrough shows you how to create a Minecraft Java Edition resource pack.\\n\\n'
             'You will load game textures, edit a block, preview it in 3D and export a ZIP.',
             'No Minecraft files are bundled with this editor.'),
            ('1. Load Minecraft textures',
             'Click Find Minecraft at the top. If your Minecraft installation cannot be found, '
             'choose Load JAR / ZIP and select your Minecraft Java client .jar file.\\n\\n'
             'The gallery will then show the available block, item, GUI and other texture images.',
             'Tip: The six initial gallery entries are placeholders, not the complete game.'),
            ('2. Find a texture',
             'Use the Search box to type a name such as stone, oak or diamond.\\n'
             'Choose block, item, gui or entity from Category to narrow the results.\\n\\n'
             'Click a thumbnail to open it in the editor.',
             'Tip: You can go back to the gallery and pick another texture.'),
            ('3. Edit pixels',
             'Use Pencil to draw, Eraser to remove pixels, Fill to color connected pixels, '
             'and Select to choose a rectangle.\\n\\n'
             'Use the color picker to change colors. Ctrl+Z undoes a change; Ctrl+Y redoes it.',
             'Tip: Start by changing just a few pixels on a simple 16×16 block.'),
            ('4. Preview in 3D',
             'The 3D preview shows your block as you work. Drag to rotate and use the mouse wheel to zoom.\\n\\n'
             'Press F11 or click Fullscreen 3D to open a larger preview. '
             'Click a visible block face to jump to its texture when supported. Press Esc to return.',
             'Note: Complex models, blockstate variants and multipart models are not fully supported.'),
            ('5. Save your work',
             'Click Save Project to keep your editable project. The program also has periodic recovery saves.\\n\\n'
             'Use Open Project later to continue. If you move or delete your original game assets, '
             'you may need to load them again.',
             'Tip: Save the project before exporting a resource pack.'),
            ('6. Validate and export',
             'Click Validate Pack to check for basic problems, then Export Pack ZIP.\\n\\n'
             'Check that the pack_format matches your Minecraft Java version. '
             'This version cannot detect the latest format automatically.',
             'Tip: Keep your editable project and exported ZIP as separate files.'),
            ('7. Use it in Minecraft',
             'Click Install ZIP to copy your exported ZIP into the Minecraft resourcepacks folder.\\n\\n'
             'Open Minecraft Java Edition, go to Options > Resource Packs, '
             'enable the pack and check your changed block in-game.',
             'If Minecraft reports an incompatible pack, verify the pack_format.'),
            ('All set!',
             'You now know the basic workflow!\\n\\n'
             'Find Minecraft → Select texture → Edit → Preview 3D → Save Project → Validate → Export → Install.\\n\\n'
             'You can restart this tutorial anytime using Help > Start Beginner Tutorial.',
             'Try editing a stone block as your first project.')
        ]
        if self.language.get()=='한국어':
            steps=[('환영합니다!', 'Minecraft Java Edition 리소스팩을 만드는 방법을 배워 봅시다.\\n\\n원본 파일을 불러오고, 블록을 편집한 뒤 3D로 확인하고 ZIP으로 내보냅니다.', '원본 Minecraft 파일은 프로그램에 포함되어 있지 않습니다.'), ('1. Minecraft 텍스처 불러오기', '상단의 마인크래프트 찾기를 클릭하세요. 자동으로 찾지 못하면 JAR / ZIP 열기를 눌러 Minecraft Java 클라이언트 JAR을 선택하세요.', '처음 보이는 6개 항목은 예시입니다.'), ('2. 텍스처 찾기', '검색창에 stone, oak, diamond 같은 이름을 입력하세요. 분류를 선택해 목록을 좁힌 다음 원하는 이미지를 클릭하세요.', '이미지를 클릭하면 편집 화면으로 이동합니다.'), ('3. 픽셀 편집하기', '연필, 지우개, 채우기, 선택 도구로 텍스처를 수정하세요. Ctrl+Z로 실행 취소, Ctrl+Y로 다시 실행할 수 있습니다.', '처음에는 간단한 16×16 블록을 추천합니다.'), ('4. 3D 미리보기', '마우스를 드래그하여 회전하고 휠로 확대하세요. F11을 눌러 전체화면을 열고, 지원되는 블록 면을 클릭하면 해당 텍스처로 이동합니다. Esc로 닫습니다.', '복잡한 블록 모델은 일부만 지원합니다.'), ('5. 프로젝트 저장', '프로젝트 저장 버튼을 눌러 편집 작업을 저장하세요. 자동 복구 기능도 있습니다. 원본 JAR을 옮기면 다시 불러와야 할 수 있습니다.', 'ZIP으로 내보내기 전에 프로젝트를 저장하세요.'), ('6. 검사 및 내보내기', '팩 검사로 기본 오류를 확인하고 팩 ZIP 내보내기를 누르세요. Minecraft 버전에 맞는 pack_format을 설정해야 합니다.', '현재 최신 pack_format 자동 감지는 지원하지 않습니다.'), ('7. Minecraft에 적용', 'ZIP 설치 버튼을 눌러 resourcepacks 폴더로 복사하세요. Minecraft Java Edition의 설정 > 리소스팩에서 활성화하세요.', '게임에서 텍스처가 실제로 바뀌었는지 확인하세요.'), ('완료!', '이제 기본 사용법을 배웠습니다!\\n\\nMinecraft 찾기 → 텍스처 선택 → 편집 → 3D 확인 → 프로젝트 저장 → 검사 → 내보내기 → 설치', '도움말 메뉴에서 튜토리얼을 다시 볼 수 있습니다.')]
        window=tk.Toplevel(self.root)
        self.tutorial_window=window
        window.title('초보자 튜토리얼 — MC Resource Table' if self.language.get()=='한국어' else 'Beginner Tutorial — MC Resource Table')
        window.geometry('660x430')
        window.minsize(540,380)
        window.configure(bg='#171b25')
        window.transient(self.root)
        window.grab_set()
        index=[0]
        body=ttk.Frame(window,padding=24);body.pack(fill='both',expand=True)
        progress=ttk.Label(body,font=('Segoe UI',10))
        progress.pack(anchor='w',pady=(0,12))
        heading=ttk.Label(body,font=('Segoe UI',18,'bold'),wraplength=590)
        heading.pack(anchor='w',pady=(0,15))
        description=ttk.Label(body,font=('Segoe UI',11),wraplength=590,justify='left')
        description.pack(anchor='w',fill='x')
        tip=ttk.Label(body,foreground='#a7c9fa',wraplength=590,justify='left')
        tip.pack(anchor='w',pady=(20,0))
        footer=ttk.Frame(window,padding=(24,12))
        footer.pack(fill='x')
        previous=ttk.Button(footer,text='◀ 이전' if self.language.get()=='한국어' else '◀ Back')
        previous.pack(side='left')
        skip=ttk.Button(footer,text='닫기' if self.language.get()=='한국어' else 'Close',command=window.destroy)
        skip.pack(side='right',padx=(10,0))
        following=ttk.Button(footer,text='다음 ▶' if self.language.get()=='한국어' else 'Next ▶')
        following.pack(side='right')
        def render():
            title,details,note=steps[index[0]]
            progress.config(text=(f'{index[0]+1} / {len(steps)} 단계' if self.language.get()=='한국어' else f'Step {index[0]+1} of {len(steps)}'))
            heading.config(text=title)
            description.config(text=details)
            tip.config(text=note)
            previous.config(state='normal' if index[0]>0 else 'disabled')
            following.config(text=('완료 ✓' if index[0]==len(steps)-1 else '다음 ▶') if self.language.get()=='한국어' else ('Finish ✓' if index[0]==len(steps)-1 else 'Next ▶'))
        def go(delta):
            if delta==1 and index[0]==len(steps)-1:
                window.destroy();return
            index[0]=max(0,min(len(steps)-1,index[0]+delta))
            render()
        previous.config(command=lambda:go(-1))
        following.config(command=lambda:go(1))
        window.bind('<Right>',lambda e:go(1))
        window.bind('<Left>',lambda e:go(-1))
        window.bind('<Escape>',lambda e:window.destroy())
        render()

    def configure_style(self):
        self.root.configure(bg='#17191f')
        s=ttk.Style()
        s.theme_use('clam')
        s.configure('.', background='#17191f', foreground='#f3f2f8', font=('Segoe UI', 10))
        s.configure('TFrame', background='#17191f')
        s.configure('TLabel', background='#17191f', foreground='#f3f2f8')
        s.configure('TButton', background='#34343f', foreground='#f6f8fc', padding=(11,9), borderwidth=0)
        s.map('TButton', background=[('active','#7854ba')])
        s.configure('Accent.TButton',background='#8058c8',foreground='#ffffff',padding=(14,10),font=('Segoe UI',10,'bold'))
        s.map('Accent.TButton',background=[('active','#9b76df')])
        s.configure('TEntry', fieldbackground='#292a33', foreground='white', insertcolor='white')
        s.configure('TCombobox', fieldbackground='#292a33', foreground='#111111')
        s.configure('TCheckbutton', background='#17191f', foreground='#e9eef8')
        s.configure('TLabelframe', background='#17191f', foreground='#e9eef8')
        s.configure('TLabelframe.Label', background='#17191f', foreground='#e9eef8')

    def create_ui(self):
        self.translatable_widgets=[]
        self.translatable_menus=[]
        # Use a compact two-row toolbar. The old single row clipped buttons
        # on 960px windows or with Windows display scaling above 100%.
        header=ttk.Frame(self.root,padding=(12,8,12,2));header.pack(fill='x')
        ttk.Label(header,text='▣  MC Resource Table 13.4',font=('Segoe UI',21,'bold')).pack(side='left')
        toolbar=ttk.Frame(self.root,padding=(12,2,12,8));toolbar.pack(fill='x')
        row1=ttk.Frame(toolbar);row1.pack(fill='x',pady=2)
        row2=ttk.Frame(toolbar);row2.pack(fill='x',pady=2)
        actions=[
            (row1,'Find Minecraft',self.find_minecraft),
            (row1,'Load JAR / ZIP',self.load_vanilla),
            (row1,'Load assets folder',self.load_folder),
            (row1,'Import PNG',self.import_png),
            (row1,'Other Assets',self.asset_manager),
            (row2,'Import Entity Model',self.import_entity_model),
            (row2,'Open Project',self.open_project),
            (row2,'Save Project',self.save_project),
            (row2,'Validate Pack',self.show_validation),
            (row2,'Export Pack ZIP',self.export),
            (row2,'Install ZIP',self.install_resource_pack),
        ]
        for parent,label,command in actions:
            button=ttk.Button(parent,text=label,command=command,style='Accent.TButton' if label=='Export Pack ZIP' else 'TButton')
            button.pack(side='left',padx=(0,6))
            self.translatable_widgets.append((button,label))
        # Menus retain all commands even on very small or high-DPI displays.
        menubar=tk.Menu(self.root)
        files=tk.Menu(menubar,tearoff=0)
        for _parent,label,command in actions:
            files.add_command(label=label,command=command)
        menubar.add_cascade(label='File & Tools',menu=files)
        for i,(_parent,label,_command) in enumerate(actions):self.translatable_menus.append((files,i,label))
        self.translatable_menus.append((menubar,menubar.index('end'),'File & Tools'))
        help_menu=tk.Menu(menubar,tearoff=0)
        help_menu.add_command(label='Start Beginner Tutorial',command=self.show_tutorial)
        help_menu.add_command(label='Quick Reference',command=self.show_quick_reference)
        menubar.add_cascade(label='Help',menu=help_menu)
        self.translatable_menus.extend([(help_menu,0,'Start Beginner Tutorial'),(help_menu,1,'Quick Reference'),(menubar,menubar.index('end'),'Help')])
        lang_menu=tk.Menu(menubar,tearoff=0)
        for language in ('English','한국어','日本語','Español'):
            lang_menu.add_radiobutton(label=language,value=language,variable=self.language,
                                     command=lambda l=language:self.set_language(l))
        menubar.add_cascade(label='Language / 언어',menu=lang_menu)
        self.root.config(menu=menubar)
        # Always-visible 3D fullscreen action, independent of the narrow editor sidebar.
        self.fullscreen_bar=ttk.Frame(self.root,padding=(16,2,16,6))
        self.fullscreen_bar.pack(fill='x')
        self.fullscreen_button=ttk.Button(
            self.fullscreen_bar,text='⛶ 전체화면 (F11) / Fullscreen',
            command=self.open_fullscreen_preview)
        self.fullscreen_button.pack(side='right',padx=8)
        self.translatable_widgets.append((self.fullscreen_button,'3D Fullscreen'))
        self.gallery=ttk.Frame(self.root,padding=(16,4,16,8))
        gallery_head=ttk.Frame(self.gallery);gallery_head.pack(fill='x',pady=(0,10))
        ttk.Label(gallery_head,text='RESOURCE GALLERY',font=('Segoe UI',17,'bold')).pack(side='left')
        ttk.Button(gallery_head,text='New texture',command=self.new_texture).pack(side='right',padx=5)
        ttk.Button(gallery_head,text='Open editor',command=self.show_editor).pack(side='right',padx=5)
        filters=ttk.Frame(self.gallery);filters.pack(fill='x',pady=(0,10))
        ttk.Label(filters,text='Search').pack(side='left',padx=(0,5))
        ttk.Entry(filters,textvariable=self.search,width=35).pack(side='left',padx=(0,14))
        ttk.Label(filters,text='Category').pack(side='left',padx=(0,5))
        ttk.Combobox(filters,textvariable=self.category,values=['All','block','item','gui','entity','particle','environment','font','colormap','misc','effect','painting','map','mob_effect','models','atlas'],state='readonly',width=18).pack(side='left')
        ttk.Label(filters,text='  Click an image to edit',foreground='#a7b7d1').pack(side='left')
        gallery_container=ttk.Frame(self.gallery);gallery_container.pack(fill='both',expand=True)
        self.gallery_canvas=tk.Canvas(gallery_container,bg='#171b25',highlightthickness=0)
        gs=ttk.Scrollbar(gallery_container,orient='vertical',command=self.gallery_canvas.yview)
        self.gallery_canvas.configure(yscrollcommand=gs.set)
        gs.pack(side='right',fill='y');self.gallery_canvas.pack(side='left',fill='both',expand=True)
        self.gallery_inner=tk.Frame(self.gallery_canvas,bg='#171b25')
        self.gallery_window=self.gallery_canvas.create_window((0,0),window=self.gallery_inner,anchor='nw')
        self.gallery_inner.bind('<Configure>',lambda e:self.gallery_canvas.configure(scrollregion=self.gallery_canvas.bbox('all')))
        self.gallery_canvas.bind('<Configure>',lambda e:self.gallery_canvas.itemconfigure(self.gallery_window,width=e.width))
        pager=ttk.Frame(self.gallery);pager.pack(fill='x',pady=8)
        ttk.Button(pager,text='◀ Previous',command=lambda:self.change_page(-1)).pack(side='left')
        self.gallery_count=ttk.Label(pager,text='');self.gallery_count.pack(side='left',padx=15)
        ttk.Button(pager,text='Next ▶',command=lambda:self.change_page(1)).pack(side='left')
        self.main=ttk.Frame(self.root,padding=(10,0,10,0))
        main=self.main
        editor_head=ttk.Frame(main);editor_head.pack(fill='x',pady=(0,8))
        ttk.Button(editor_head,text='← Back to gallery',command=self.show_gallery).pack(side='left')
        ttk.Label(editor_head,text='✎  2D 편집 (텍스처)    ◇  3D 미리보기 (모델)',font=('Segoe UI',13,'bold'),foreground='#b792fa').pack(side='left',padx=14)
        workspace=ttk.Panedwindow(main,orient='horizontal')
        workspace.pack(fill='both',expand=True)
        main=workspace
        # Visual redesign: thumbnail library and category navigation are visible alongside the editor.
        left=ttk.Frame(main,width=300)
        main.add(left,weight=1)
        ttk.Label(left,text='리소스 갤러리  /  RESOURCE GALLERY',font=('Segoe UI',12,'bold'),foreground='#bd9af7').pack(anchor='w',pady=(4,12))
        ttk.Entry(left,textvariable=self.search).pack(fill='x',pady=(0,8))
        category_bar=ttk.Frame(left);category_bar.pack(fill='x',pady=(0,8))
        categories=[('모두','All'),('블록','block'),('아이템','item'),('GUI','gui'),('엔티티','entity')]
        for text,value in categories:
            ttk.Radiobutton(category_bar,text=text,variable=self.category,value=value).pack(side='left',padx=(0,7))
        self.category.trace_add('write',lambda *_:self.on_filter_change())
        self.search.trace_add('write',lambda *_:self.on_filter_change())
        thumb_container=ttk.Frame(left);thumb_container.pack(fill='both',expand=True)
        self.side_canvas=tk.Canvas(thumb_container,bg='#202127',highlightthickness=0)
        side_scroll=ttk.Scrollbar(thumb_container,orient='vertical',command=self.side_canvas.yview)
        self.side_canvas.configure(yscrollcommand=side_scroll.set)
        side_scroll.pack(side='right',fill='y')
        self.side_canvas.pack(side='left',fill='both',expand=True)
        self.side_inner=tk.Frame(self.side_canvas,bg='#202127')
        self.side_window=self.side_canvas.create_window((0,0),window=self.side_inner,anchor='nw')
        self.side_inner.bind('<Configure>',lambda e:self.side_canvas.configure(scrollregion=self.side_canvas.bbox('all')))
        self.side_canvas.bind('<Configure>',lambda e:self.side_canvas.itemconfigure(self.side_window,width=e.width))
        self.side_photos=[]
        ttk.Button(left,text='◀ 이전',command=lambda:self.change_page(-1)).pack(side='left',pady=8)
        ttk.Button(left,text='다음 ▶',command=lambda:self.change_page(1)).pack(side='right',pady=8)
        self.listbox=tk.Listbox(left,height=1)
        self.listbox.bind('<<ListboxSelect>>',self.select_from_list)

        center=ttk.Frame(main,width=620)
        main.add(center,weight=4)
        ttk.Label(center,text='✎  PIXEL EDITOR',font=('Segoe UI',12,'bold'),foreground='#c5a4ff').pack(anchor='w',pady=(5,7))
        self.path_label=ttk.Label(center,text=self.current);self.path_label.pack(anchor='w',pady=(0,7))
        toolbar=ttk.Frame(center);toolbar.pack(fill='x',pady=(0,8))
        for name in ['Pencil','Eraser','Fill','Line','Rectangle','Select','Move','Eyedropper']:
            ttk.Radiobutton(toolbar,text=name,variable=self.tool,value=name,command=self.draw).pack(side='left',padx=2)
        self.canvas=tk.Canvas(center,bg='#292b34',highlightthickness=1,highlightbackground='#43516a',cursor='crosshair')
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.canvas.bind('<ButtonPress-1>',self.mouse_down)
        self.canvas.bind('<B1-Motion>',self.mouse_drag)
        self.canvas.bind('<ButtonRelease-1>',self.mouse_up)
        self.canvas.bind('<Button-3>',lambda e:self.choose_color())
        self.canvas.bind('<MouseWheel>',self.mouse_wheel)
        bottom=ttk.Frame(center);bottom.pack(fill='x',pady=8)
        ttk.Button(bottom,text='Undo',command=self.undo).pack(side='left',padx=2)
        ttk.Button(bottom,text='Redo',command=self.redo).pack(side='left',padx=2)
        ttk.Button(bottom,text='Crop to selection',command=self.crop_selection).pack(side='left',padx=2)
        ttk.Button(bottom,text='Resize…',command=self.resize_image).pack(side='left',padx=2)
        ttk.Button(bottom,text='Zoom −',command=lambda:self.editor_zoom(0.8)).pack(side='left',padx=2)
        ttk.Button(bottom,text='Zoom +',command=lambda:self.editor_zoom(1.25)).pack(side='left',padx=2)
        ttk.Button(bottom,text='Fit',command=self.editor_fit).pack(side='left',padx=2)
        ttk.Checkbutton(bottom,text='Pixel grid',variable=self.grid_on,command=self.draw).pack(side='right')

        right=ttk.Frame(main,width=265)
        main.add(right,weight=1)
        ttk.Label(right,text='◇  3D 미리보기  /  PREVIEW',font=('Segoe UI',11,'bold'),foreground='#c5a4ff').pack(anchor='w',pady=(5,5))
        self.block_preview=tk.Canvas(right,width=230,height=225,bg='#22242e',highlightthickness=0)
        self.block_preview.pack(pady=(0,5))
        self.block_preview.bind('<Double-Button-1>',lambda e:self.open_fullscreen_preview())
        self.block_preview.bind('<ButtonPress-1>',self.preview_press)
        self.block_preview.bind('<B1-Motion>',self.preview_drag)
        self.block_preview.bind('<ButtonRelease-1>',self.preview_release)
        self.block_preview.bind('<MouseWheel>',self.preview_wheel)
        self.block_preview.bind('<Button-4>',lambda e:self.preview_zoom_by(1.1))
        self.block_preview.bind('<Button-5>',lambda e:self.preview_zoom_by(1/1.1))
        ttk.Label(right,text='Drag horizontally AND vertically · Scroll to zoom',foreground='#a7b7d1',wraplength=225).pack(anchor='w')
        controls=ttk.Frame(right);controls.pack(fill='x')
        ttk.Button(controls,text='−',width=3,command=lambda:self.preview_zoom_by(1/1.2)).pack(side='left')
        ttk.Button(controls,text='Reset view',command=self.preview_reset).pack(side='left',expand=True)
        ttk.Button(controls,text='+',width=3,command=lambda:self.preview_zoom_by(1.2)).pack(side='right')
        ttk.Button(right,text='⛶ Fullscreen 3D',command=self.open_fullscreen_preview).pack(fill='x',pady=(6,8))
        self.face_frame=ttk.Frame(right);self.face_frame.pack(fill='x',pady=(0,12))
        ttk.Button(right,text='✎  More editing tools / 추가 도구',command=self.open_extra_tools).pack(fill='x',pady=(2,12))
        ttk.Label(right,text='▤  레이어  /  LAYERS',font=('Segoe UI',11,'bold'),foreground='#c5a4ff').pack(anchor='w',pady=(14,5))
        self.layer_list=tk.Listbox(right,height=6,bg='#222b3b',fg='#edf3ff',selectbackground='#426ab1',exportselection=False)
        self.layer_list.pack(fill='x')
        self.layer_list.bind('<<ListboxSelect>>',self.choose_layer)
        layer_buttons=ttk.Frame(right);layer_buttons.pack(fill='x',pady=4)
        for title,fn in [('+',self.add_layer),('−',self.remove_layer),('↑',self.layer_up),('↓',self.layer_down),('Show/Hide',self.toggle_layer)]:
            ttk.Button(layer_buttons,text=title,command=fn).pack(side='left',padx=1)
        ttk.Label(right,text='Select a layer to edit it. Hidden layers\nare excluded from the exported PNG.',foreground='#a7b7d1').pack(anchor='w',pady=4)
        ttk.Label(right,text='PACK SETTINGS',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(18,7))
        ttk.Label(right,text='Description').pack(anchor='w');ttk.Entry(right,textvariable=self.pack_name).pack(fill='x',pady=3)
        ttk.Label(right,text='pack_format (Java)').pack(anchor='w',pady=(8,0));ttk.Entry(right,textvariable=self.format).pack(fill='x',pady=3)
        ttk.Label(right,text='Check the pack format required by\nyour exact Minecraft version.\n\nGUI textures can be edited too:\nchoose the GUI category.',foreground='#a7b7d1',wraplength=230).pack(anchor='w',pady=12)
        ttk.Label(self.root,textvariable=self.status,padding=(12,8),foreground='#b7c9e4').pack(fill='x')
        self.refresh_list()
        self.register_translatable_widgets(self.root)

    def editor_fit(self):
        self.zoom_override=None
        del self.zoom_override
        self.draw()

    def editor_zoom(self,factor):
        self.zoom_override=max(1,min(96,int(round(getattr(self,'zoom_override',self.zoom)*factor))))
        self.draw()
        self.status.set(f'Editor zoom: {self.zoom} pixels per texture pixel')

    def open_extra_tools(self):
        window=tk.Toplevel(self.root)
        window.title('Editing tools / 편집 도구')
        window.geometry('340x570')
        body=ttk.Frame(window,padding=16);body.pack(fill='both',expand=True)
        actions=[('Choose color',self.choose_color),('Copy selection',self.copy_selection),('Cut selection',self.cut_selection),('Paste selection',self.paste_selection),('Delete selection',self.delete_selection),('Select all',self.select_all),('Clear selection',self.clear_selection),('Clear texture',self.clear_image),('Flip horizontally',lambda:self.transform_selection('flip_h')),('Flip vertically',lambda:self.transform_selection('flip_v')),('Rotate 90°',lambda:self.transform_selection('rotate')),('Save current texture',self.save)]
        for label,command in actions:ttk.Button(body,text=label,command=command).pack(fill='x',pady=3)

    def sync_layer(self):
        if self.layers:self.layers[self.active_layer]['image']=self.image

    def composite_layers(self):
        self.sync_layer()
        out=Image.new('RGBA',self.image.size,(0,0,0,0))
        for layer in self.layers:
            if layer['visible']:
                im=layer['image']
                if im.size!=out.size:im=im.resize(out.size,Image.Resampling.NEAREST)
                out=Image.alpha_composite(out,im)
        return out

    def refresh_layers(self):
        if not hasattr(self,'layer_list'):return
        self.layer_list.delete(0,'end')
        for layer in reversed(self.layers):
            self.layer_list.insert('end',('● ' if layer['visible'] else '○ ')+layer['name'])
        if self.layers:self.layer_list.selection_set(len(self.layers)-1-self.active_layer)

    def choose_layer(self,event=None):
        idx=self.layer_list.curselection()
        if not idx:return
        target=len(self.layers)-1-idx[0]
        if target==self.active_layer:return
        self.sync_layer();self.active_layer=target;self.image=self.layers[target]['image']
        self.history=[];self.redo_stack=[];self.selection=None;self.draw()

    def add_layer(self):
        name=simpledialog.askstring('New layer','Layer name:',initialvalue=f'Layer {len(self.layers)+1}',parent=self.root)
        if not name:return
        self.sync_layer()
        self.layers.insert(self.active_layer+1,{'name':name,'visible':True,'image':Image.new('RGBA',self.image.size,(0,0,0,0))})
        self.active_layer+=1;self.image=self.layers[self.active_layer]['image']
        self.history=[];self.redo_stack=[];self.selection=None;self.dirty=True;self.refresh_layers();self.draw()

    def remove_layer(self):
        if len(self.layers)==1:messagebox.showinfo('Layers','Keep at least one layer.');return
        self.layers.pop(self.active_layer);self.active_layer=min(self.active_layer,len(self.layers)-1)
        self.image=self.layers[self.active_layer]['image'];self.history=[];self.redo_stack=[]
        self.selection=None;self.dirty=True;self.refresh_layers();self.draw()

    def layer_up(self):self.shift_layer(1)
    def layer_down(self):self.shift_layer(-1)
    def shift_layer(self,direction):
        dest=self.active_layer+direction
        if not 0<=dest<len(self.layers):return
        self.sync_layer();self.layers[self.active_layer],self.layers[dest]=self.layers[dest],self.layers[self.active_layer]
        self.active_layer=dest;self.dirty=True;self.refresh_layers();self.draw()

    def toggle_layer(self):
        layer=self.layers[self.active_layer];layer['visible']=not layer['visible']
        self.dirty=True;self.refresh_layers();self.draw()

    def resize_other_layers(self,size,crop=None):
        self.sync_layer()
        for i,layer in enumerate(self.layers):
            if i==self.active_layer:continue
            layer['image']=layer['image'].crop(crop) if crop else layer['image'].resize(size,Image.Resampling.NEAREST)

    def valid(self,p):
        return bool(VALID.fullmatch(p)) and '..' not in p.split('/') and not p.endswith('/')

    def refresh_list(self):
        q=self.search.get().lower().strip();cat=self.category.get()
        self.visible=[p for p in sorted(self.names | set(self.base) | set(self.edits)) if (cat=='All' or p.startswith(cat+'/')) and q in p]
        self.listbox.delete(0,'end')
        for p in self.visible:self.listbox.insert('end',('● ' if p in self.edits else '  ')+p)
        if hasattr(self,'gallery_inner') and self.gallery.winfo_manager():
            self.render_gallery()
        if hasattr(self,'side_inner'):self.render_side_gallery()

    def on_filter_change(self):
        self.gallery_page=0
        self.refresh_list()

    def show_gallery(self):
        self.save(silent=True)
        self.main.pack_forget()
        self.gallery.pack(fill='both',expand=True)
        self.render_gallery()

    def show_editor(self):
        self.gallery.pack_forget()
        self.main.pack(fill='both',expand=True)
        self.draw()
        self.render_side_gallery()

    def change_page(self,delta):
        count=max(1,(len(self.visible)+self.gallery_page_size-1)//self.gallery_page_size)
        self.gallery_page=max(0,min(count-1,self.gallery_page+delta))
        self.render_gallery()
        if hasattr(self,'side_inner'):self.render_side_gallery()
        self.gallery_canvas.yview_moveto(0)

    def edit_from_gallery(self,path):
        self.open_path(path)
        self.show_editor()

    def render_gallery(self):
        if not hasattr(self,'gallery_inner'):return
        for child in self.gallery_inner.winfo_children():child.destroy()
        self.gallery_photos=[]
        total=len(self.visible)
        pages=max(1,(total+self.gallery_page_size-1)//self.gallery_page_size)
        self.gallery_page=min(self.gallery_page,pages-1)
        begin=self.gallery_page*self.gallery_page_size
        self.gallery_count.config(text=f'{total:,} textures  |  Page {self.gallery_page+1} of {pages}')
        if total==0:
            tk.Label(self.gallery_inner,text='No matching textures. Load your Minecraft Java client JAR or choose another category.',bg='#171b25',fg='#d5e0f5',font=('Segoe UI',12)).pack(pady=35)
            return
        columns=6
        for index,path in enumerate(self.visible[begin:begin+self.gallery_page_size]):
            r,c=divmod(index,columns)
            card=tk.Frame(self.gallery_inner,bg='#252e40',highlightbackground='#39465f',highlightthickness=1,width=154,height=155)
            card.grid(row=r,column=c,padx=7,pady=7,sticky='nsew')
            card.grid_propagate(False)
            try:
                image=self.image_for(path)
                image.thumbnail((88,88),Image.Resampling.NEAREST)
                if image.width and image.height:
                    scale=max(1,min(88//image.width,88//image.height))
                    image=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
                photo=ImageTk.PhotoImage(image)
                self.gallery_photos.append(photo)
                img=tk.Label(card,image=photo,bg='#252e40',cursor='hand2')
                img.pack(pady=(8,3))
                img.bind('<Button-1>',lambda e,p=path:self.edit_from_gallery(p))
            except Exception:
                tk.Label(card,text='?',bg='#252e40',fg='white').pack(pady=24)
            label=path.split('/')[-1].replace('_',' ').title()
            if len(label)>21:label=label[:19]+'…'
            tk.Label(card,text=label,bg='#252e40',fg='#f1f5ff',font=('Segoe UI',9,'bold')).pack()
            tk.Label(card,text=path.split('/')[0]+('  • edited' if path in self.edits else ''),bg='#252e40',fg='#a9b9d6',font=('Segoe UI',8)).pack()
            tk.Button(card,text='Edit',command=lambda p=path:self.edit_from_gallery(p),bg='#385b91',fg='white',relief='flat',cursor='hand2').pack(pady=(3,4))
        for c in range(columns):self.gallery_inner.grid_columnconfigure(c,weight=1)

    def render_side_gallery(self):
        if not hasattr(self,'side_inner'):return
        for widget in self.side_inner.winfo_children():widget.destroy()
        self.side_photos=[]
        pages=max(1,(len(self.visible)+23)//24)
        self.gallery_page=min(self.gallery_page,pages-1)
        for i,path in enumerate(self.visible[self.gallery_page*24:(self.gallery_page+1)*24]):
            frame=tk.Frame(self.side_inner,bg='#30303a',highlightbackground='#8058c8' if path==self.current else '#41414b',highlightthickness=2 if path==self.current else 1,width=120,height=125,cursor='hand2')
            frame.grid(row=i//3,column=i%3,padx=5,pady=6,sticky='nsew')
            frame.grid_propagate(False)
            try:
                image=self.image_for(path)
                image.thumbnail((72,72),Image.Resampling.NEAREST)
                scale=max(1,min(72//max(1,image.width),72//max(1,image.height)))
                photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST))
                self.side_photos.append(photo)
                label=tk.Label(frame,image=photo,bg='#30303a',cursor='hand2')
                label.pack(pady=(9,3))
                label.bind('<Button-1>',lambda e,p=path:self.open_path(p))
            except Exception:pass
            name=path.split('/')[-1]+'.png'
            text=tk.Label(frame,text=name[:17],bg='#30303a',fg='#f0eef8',font=('Segoe UI',9),cursor='hand2')
            text.pack()
            text.bind('<Button-1>',lambda e,p=path:self.open_path(p))
        for c in range(3):self.side_inner.grid_columnconfigure(c,weight=1)

    def select_from_list(self,_):
        idx=self.listbox.curselection()
        if idx:self.open_path(self.visible[idx[0]]);self.show_editor()

    def image_for(self,p):
        if p in self.edits:return self.edits[p].copy()
        if p in self.base:
            try:
                with Image.open(io.BytesIO(self.base[p])) as im:return im.convert('RGBA').copy()
            except Exception:pass
        return Image.new('RGBA',(16,16),(0,0,0,0))

    def open_path(self,p,initial=False):
        if not self.valid(p):return
        if not initial:self.save(silent=True)
        self.current=p
        if p in self.layer_docs:
            self.layers=[{'name':a['name'],'visible':a['visible'],'image':a['image'].copy()} for a in self.layer_docs[p]]
        else:
            self.layers=[{'name':'Base','visible':True,'image':self.image_for(p)}]
        self.active_layer=0
        self.image=self.layers[0]['image']
        self.refresh_layers()
        self.selection=None;self.history=[];self.redo_stack=[];self.dirty=False
        self.path_label.config(text=p+'  —  '+str(self.image.width)+' × '+str(self.image.height))
        self.names.add(p);self.refresh_list();self.draw()
        self.status.set('Editing '+p)
        if hasattr(self,'side_inner'):self.render_side_gallery()
        self.update_block_preview()

    def block_faces(self):
        if not self.current.startswith('block/'):
            return []
        name=self.current.split('/')[-1]
        suffixes=['_top','_bottom','_side','_front','_back','_north','_south','_east','_west','_up','_down']
        stem=name
        for suffix in suffixes:
            if stem.endswith(suffix):stem=stem[:-len(suffix)];break
        candidates={
            'Top':[f'block/{stem}_top',f'block/{stem}_up',f'block/{stem}'],
            'Side':[f'block/{stem}_side',f'block/{stem}',f'block/{stem}_front'],
            'Bottom':[f'block/{stem}_bottom',f'block/{stem}_down',f'block/{stem}'],
        }
        available=self.names|set(self.base)|set(self.edits)
        result=[]
        for label,opts in candidates.items():
            path=next((v for v in opts if v in available),None)
            if path:result.append((label,path))
        # Add all actual related texture faces as accessible buttons.
        for suffix in ['_front','_back','_north','_south','_east','_west']:
            path=f'block/{stem}{suffix}'
            if path in available and path not in [x[1] for x in result]:result.append((suffix[1:].title(),path))
        return result

    def resolve_block_model(self):
        """Best-effort resolve a matching vanilla model and its parent chain."""
        if not self.current.startswith('block/'):return None
        stem=self.current.split('/')[-1]
        for suffix in ('_top','_bottom','_side','_front','_back','_north','_south','_east','_west','_up','_down'):
            if stem.endswith(suffix):stem=stem[:-len(suffix)];break
        candidates=[stem,stem+'_inventory']
        for name in candidates:
            key='assets/minecraft/models/block/'+name+'.json'
            if key in self.other_assets:
                return self._resolve_model(key,set())
        return None

    def _resolve_model(self,key,seen):
        if key in seen or len(seen)>20:return None
        seen.add(key)
        raw=self.other_assets.get(key)
        if not raw:return None
        try:model=json.loads(raw.decode('utf-8'))
        except (ValueError,UnicodeError):return None
        parent=model.get('parent','')
        inherited={}
        if parent and ':' not in parent:parent='minecraft:'+parent
        if parent.startswith('minecraft:'):
            inherited=self._resolve_model('assets/minecraft/models/'+parent.split(':',1)[1]+'.json',seen) or {}
        textures=dict(inherited.get('textures',{}))
        textures.update(model.get('textures',{}))
        return {'textures':textures,'elements':model.get('elements',inherited.get('elements',[]))}

    def model_texture(self,ref,texture_vars):
        for _ in range(12):
            if not isinstance(ref,str):return None
            if not ref.startswith('#'):break
            ref=texture_vars.get(ref[1:])
        if not ref or ref.startswith('#'):return None
        if ':' in ref:
            namespace,ref=ref.split(':',1)
            if namespace!='minecraft':return None
        if not ref.startswith(('block/','item/')):return None
        return ref

    def model_geometry(self):
        model=self.resolve_block_model()
        if not model or not model.get('elements'):return None
        quads=[]
        # Minecraft coordinates are 0..16. Convert to centered cube coordinates.
        for element in model['elements'][:128]:
            a=element.get('from',[0,0,0]);b=element.get('to',[16,16,16])
            if len(a)!=3 or len(b)!=3:continue
            x0,y0,z0=[(float(v)-8)/8 for v in a]
            x1,y1,z1=[(float(v)-8)/8 for v in b]
            surfaces={
              'up':[(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)],
              'down':[(x0,y0,z1),(x1,y0,z1),(x1,y0,z0),(x0,y0,z0)],
              'north':[(x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)],
              'south':[(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],
              'east':[(x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1)],
              'west':[(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)],
            }
            for direction,face in element.get('faces',{}).items():
                if direction not in surfaces:continue
                tex=self.model_texture(face.get('texture'),model['textures'])
                if not tex:continue
                uv=face.get('uv',[0,0,16,16])
                if len(uv)!=4:uv=[0,0,16,16]
                u0,v0,u1,v1=[float(v)/16 for v in uv]
                uvcoords=[(u0,v1),(u1,v1),(u1,v0),(u0,v0)]
                turns=int(face.get('rotation',0))//90%4
                uvcoords=uvcoords[turns:]+uvcoords[:turns]
                quads.append((surfaces[direction],uvcoords,tex,0.9 if direction=='up' else 0.75 if direction=='down' else 0.85))
        return quads or None

    def import_entity_model(self):
        """Import Blockbench cuboid model JSON (.bbmodel), attached to current texture.

        This is an opt-in model import, NOT automatic extraction from client JAR.
        """
        if not self.current.startswith('entity/'):
            messagebox.showinfo('Entity model','Select an entity texture first.');return
        filename=filedialog.askopenfilename(title='Import Blockbench entity model',filetypes=[('Blockbench model','*.bbmodel'),('JSON model','*.json')])
        if not filename:return
        try:
            data=json.loads(Path(filename).read_text(encoding='utf-8'))
            if not isinstance(data,dict) or not isinstance(data.get('elements'),list):
                raise ValueError('Expected a Blockbench model with an elements array.')
            cubes=[e for e in data['elements'] if isinstance(e,dict) and e.get('type','cube')=='cube' and isinstance(e.get('faces'),dict)]
            if not cubes:raise ValueError('No UV-mapped cubes found. Export a cuboid Blockbench model.')
            self.entity_models[self.current]=data
            self.preview_face_signature=None
            self.schedule_preview(force=True)
            self.status.set(f'Imported {len(cubes)} model cubes for {self.current} (Blockbench)')
            messagebox.showinfo('Model imported',f'Loaded {len(cubes)} cubes for {self.current}.\n\nThis model is for preview only; it is not included in the resource pack.\nGroup transforms, meshes and animations are not yet supported.')
        except (OSError,UnicodeError,ValueError,TypeError) as exc:
            messagebox.showerror('Cannot import model',str(exc))

    def imported_entity_geometry(self):
        """Render cuboid face UVs from a user-supplied Blockbench model."""
        data=self.entity_models.get(self.current)
        if not data:return None
        img=self.composite_layers();iw,ih=img.size
        resolution=data.get('resolution') or {}
        tw=max(1,float(resolution.get('width',iw)))
        th=max(1,float(resolution.get('height',ih)))
        quads=[]
        for cube in data.get('elements',[])[:512]:
            if not isinstance(cube,dict) or cube.get('type','cube')!='cube':continue
            a=cube.get('from');b=cube.get('to');faces=cube.get('faces',{})
            if not isinstance(a,list) or not isinstance(b,list) or len(a)!=3 or len(b)!=3:continue
            try:
                x0,y0,z0=[(float(v)-8)/8 for v in a];x1,y1,z1=[(float(v)-8)/8 for v in b]
            except (ValueError,TypeError):continue
            surfaces={
              'up':[(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)],
              'down':[(x0,y0,z1),(x1,y0,z1),(x1,y0,z0),(x0,y0,z0)],
              'north':[(x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0)],
              'south':[(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],
              'east':[(x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1)],
              'west':[(x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)],
            }
            # Apply per-cube Euler rotation around the Blockbench origin.
            origin=cube.get('origin',[8,8,8]);angles=cube.get('rotation',[0,0,0])
            if len(origin)==3 and len(angles)==3:
                try:
                    pivot=[(float(v)-8)/8 for v in origin]
                    angles=[math.radians(float(v)) for v in angles]
                    def rotate(v):
                        x,y,z=[v[i]-pivot[i] for i in range(3)]
                        ax,ay,az=angles
                        y,z=y*math.cos(ax)-z*math.sin(ax),y*math.sin(ax)+z*math.cos(ax)
                        x,z=x*math.cos(ay)+z*math.sin(ay),-x*math.sin(ay)+z*math.cos(ay)
                        x,y=x*math.cos(az)-y*math.sin(az),x*math.sin(az)+y*math.cos(az)
                        return (x+pivot[0],y+pivot[1],z+pivot[2])
                    surfaces={k:[rotate(v) for v in verts] for k,verts in surfaces.items()}
                except (ValueError,TypeError):pass
            for direction,face in faces.items():
                if direction not in surfaces or not isinstance(face,dict) or not isinstance(face.get('uv'),list):continue
                uv=face['uv']
                if len(uv)!=4:continue
                try:u0,v0,u1,v1=[float(v) for v in uv]
                except (TypeError,ValueError):continue
                coords=[(u0/tw,v1/th),(u0/tw,v0/th),(u1/tw,v0/th),(u1/tw,v1/th)]
                turns=int(face.get('rotation',0))//90%4
                coords=coords[turns:]+coords[:turns]
                quads.append((surfaces[direction],coords,self.current,.9 if direction=='up' else .8))
        return quads or None

    def entity_geometry(self):
        """Approximate vanilla cuboid previews for common 64x32/64x64 mob atlases.

        Entity mesh definitions live in Minecraft Java code, not resource-pack JSON.
        Unsupported mobs intentionally show a message instead of a misleading cube.
        """
        if not self.current.startswith('entity/'):return None
        imported=self.imported_entity_geometry()
        if imported:return imported
        path=self.current
        filename=path.rsplit('/',1)[-1]
        kind=None
        if filename in ('steve','alex','wide','slim','player','zombie','husk','drowned','skeleton','stray','wither_skeleton') or any(x in path for x in ('/zombie/','/skeleton/','/player/')):
            kind='humanoid'
        elif filename in ('creeper','charged_creeper') or '/creeper/' in path:kind='creeper'
        elif filename in ('pig','cow','mooshroom','sheep','sheep_fur') or any(x in path for x in ('/cow/','/pig/','/sheep/')):kind='quadruped'
        if kind is None:return None
        atlas=self.composite_layers()
        aw,ah=atlas.size
        if aw<32 or ah<16:return None
        # Cuboids in model space: center, dimensions, UV origin in 64x32 vanilla atlas units.
        if kind=='humanoid':
            boxes=[((0,.75,0),(.72,.72,.72),(0,0)),((0,-.12,0),(.72,1.05,.38),(16,16)),
                   ((-.52,-.13,0),(.30,1.02,.36),(40,16)),((.52,-.13,0),(.30,1.02,.36),(40,16)),
                   ((-.19,-1.04,0),(.32,.9,.36),(0,16)),((.19,-1.04,0),(.32,.9,.36),(0,16))]
        elif kind=='creeper':
            boxes=[((0,.7,0),(.9,.9,.9),(0,0)),((0,-.25,0),(.82,1.2,.48),(16,16)),
                   ((-.29,-1.04,-.27),(.3,.58,.34),(0,16)),((.29,-1.04,-.27),(.3,.58,.34),(0,16)),
                   ((-.29,-1.04,.27),(.3,.58,.34),(0,16)),((.29,-1.04,.27),(.3,.58,.34),(0,16))]
        else:
            boxes=[((0,.30,0),(.8,.7,.78),(0,0)),((0,-.34,0),(1.05,.9,1.45),(28,8)),
                   ((-.34,-1.04,-.47),(.27,.72,.3),(0,16)),((.34,-1.04,-.47),(.27,.72,.3),(0,16)),
                   ((-.34,-1.04,.47),(.27,.72,.3),(0,16)),((.34,-1.04,.47),(.27,.72,.3),(0,16))]
        quads=[]
        # Each box gets Minecraft's usual unfolded box UV layout. The dimensions
        # are approximate; UV placement is most useful on 64x32 mob skins.
        for center,dims,origin in boxes:
            x,y,z=center;w,h,d=dims
            x0,x1=x-w/2,x+w/2;y0,y1=y-h/2,y+h/2;z0,z1=z-d/2,z+d/2
            a,b=origin
            # Texture widths in pixels, scaled to classic 64-unit layout.
            tw=max(1,round(w*8));th=max(1,round(h*8));td=max(1,round(d*8))
            surfaces=[
              ([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)],(a+td,b,a+td+tw,b+td),.98),
              ([(x0,y0,z1),(x1,y0,z1),(x1,y0,z0),(x0,y0,z0)],(a+td+tw,b,a+td+tw+tw,b+td),.65),
              ([(x0,y0,z1),(x0,y1,z1),(x1,y1,z1),(x1,y0,z1)],(a+td,b+td,a+td+tw,b+td+th),.86),
              ([(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z0)],(a+td+tw+td,b+td,a+td+tw+td+tw,b+td+th),.76),
              ([(x0,y0,z0),(x0,y1,z0),(x0,y1,z1),(x0,y0,z1)],(a,b+td,a+td,b+td+th),.75),
              ([(x1,y0,z1),(x1,y1,z1),(x1,y1,z0),(x1,y0,z0)],(a+td+tw,b+td,a+td+tw+td,b+td+th),.81),
            ]
            for verts,uvbox,shade in surfaces:
                u0,v0,u1,v1=uvbox
                uv=[(u0/64,v1/32),(u0/64,v0/32),(u1/64,v0/32),(u1/64,v1/32)]
                quads.append((verts,uv,path,shade))
        return quads

    def open_fullscreen_preview(self):
        if self.fullscreen_window is not None and self.fullscreen_window.winfo_exists():
            self.fullscreen_window.lift()
            self.fullscreen_window.focus_force()
            return
        window=tk.Toplevel(self.root)
        self.fullscreen_window=window
        window.title('MC Resource Table — Fullscreen 3D Preview')
        window.configure(bg='#111722')
        window.attributes('-fullscreen',True)
        window.protocol('WM_DELETE_WINDOW',self.close_fullscreen_preview)
        window.bind('<Escape>',lambda e:self.close_fullscreen_preview())
        window.bind('<F11>',lambda e:self.close_fullscreen_preview())
        toolbar=ttk.Frame(window)
        toolbar.pack(side='top',fill='x')
        ttk.Label(toolbar,text='3D Preview · Click face to edit · Drag to rotate · Wheel to zoom · Esc to exit').pack(side='left',padx=12,pady=8)
        ttk.Button(toolbar,text='Close (Esc)',command=self.close_fullscreen_preview).pack(side='right',padx=10)
        ttk.Button(toolbar,text='Reset',command=self.preview_reset).pack(side='right',padx=5)
        canvas=tk.Canvas(window,bg='#111722',highlightthickness=0)
        canvas.pack(fill='both',expand=True)
        self.fullscreen_canvas=canvas
        canvas.bind('<ButtonPress-1>',self.preview_press)
        canvas.bind('<B1-Motion>',self.preview_drag)
        canvas.bind('<ButtonRelease-1>',self.preview_release)
        canvas.bind('<MouseWheel>',self.preview_wheel)
        canvas.bind('<Button-4>',lambda e:self.preview_zoom_by(1.1))
        canvas.bind('<Button-5>',lambda e:self.preview_zoom_by(1/1.1))
        canvas.bind('<Configure>',lambda e:self.schedule_preview())
        window.focus_force()
        self.schedule_preview()

    def close_fullscreen_preview(self):
        if self.fullscreen_window is not None:
            try:self.fullscreen_window.destroy()
            except tk.TclError:pass
        self.fullscreen_window=None
        self.fullscreen_canvas=None
        self.fullscreen_photo=None
        self.preview_pick=None
        self.preview_interactive=False
        self.schedule_preview(force=True)

    def preview_press(self,event):
        self.preview_interactive=True
        self.view_drag_start=(event.x,event.y,self.view_yaw,self.view_pitch)

    def preview_release(self,event):
        if self.view_drag_start is None:return
        sx,sy,_,_=self.view_drag_start
        self.view_drag_start=None
        self.preview_interactive=False
        self.schedule_preview(force=True)
        # A drag rotates; only a short click selects a texture.
        if abs(event.x-sx)+abs(event.y-sy)>8:return
        if self.preview_pick is None:return
        ox,oy=self.preview_pick_offset
        px=int(event.x-ox);py=int(event.y-oy)
        size=self.preview_pick_size
        if not (0<=px<size and 0<=py<size):return
        path=self.preview_pick[py*size+px]
        if not path:return
        self.close_fullscreen_preview()
        self.open_path(path)
        self.status.set('3D face selected: '+path)

    def preview_drag(self,event):
        if self.view_drag_start is None:return
        x,y,yaw,pitch=self.view_drag_start
        self.view_yaw=yaw+(event.x-x)*0.015
        self.view_pitch=max(-3.12,min(3.12,pitch+(event.y-y)*0.018))
        self.schedule_preview()

    def preview_zoom_by(self,factor):
        self.view_zoom=max(0.45,min(2.7,self.view_zoom*factor))
        self.schedule_preview()

    def preview_wheel(self,event):
        self.preview_zoom_by(1.12 if event.delta>0 else 1/1.12)

    def preview_reset(self):
        self.view_yaw=0.65
        self.view_pitch=0.45
        self.view_zoom=1.0
        self.schedule_preview()

    def schedule_preview(self,force=False):
        if not hasattr(self,'block_preview'):return
        if force and self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
            self.preview_job=None
        # Coalesce mouse-motion events instead of restarting an 80 ms debounce.
        if self.preview_job is None:
            self.preview_job=self.root.after(1 if force else 16,self.update_block_preview)

    def update_block_preview(self):
        self.preview_job=None
        if not hasattr(self,'block_preview'):return
        faces=self.block_faces()
        entity_quads=self.entity_geometry() if self.current.startswith('entity/') else None
        signature=tuple(faces) if not entity_quads else (('Entity texture',self.current),)
        if signature!=self.preview_face_signature:
            for w in self.face_frame.winfo_children():w.destroy()
            self.preview_face_signature=signature
        self.block_preview.delete('all')
        if not faces:
            self.block_preview.create_text(108,100,text='3D cube preview available\\nfor block textures',fill='#aab9d5',justify='center')
            return
        if faces and not self.face_frame.winfo_children():
            for label,path in faces:
                ttk.Button(self.face_frame,text=label,command=lambda p=path:self.open_path(p)).pack(fill='x',pady=1)
        if entity_quads and not self.face_frame.winfo_children():
            ttk.Button(self.face_frame,text='Entity texture',command=lambda p=self.current:self.open_path(p)).pack(fill='x',pady=1)
        mapped=dict(faces)
        def tex(label):
            path=mapped.get(label,self.current)
            if path==self.current:return self.composite_layers()
            return self.image_for(path)
        top=tex('Top'); side=tex('Side'); bottom=tex('Bottom')
        # Six independently oriented textured cube faces, with orbit/zoom and depth sorting.
        # Geometry is rendered using perspective projection and per-pixel triangle sampling.
        full=self.fullscreen_canvas is not None and self.fullscreen_canvas.winfo_exists()
        target_size=max(216,min(720,self.fullscreen_canvas.winfo_width(),self.fullscreen_canvas.winfo_height())) if full else 216
        size=min(216,target_size) if self.preview_interactive else target_size
        out=Image.new('RGBA',(size,size),(0,0,0,0))
        pixels=out.load()
        zbuf=[float('inf')]*(size*size)
        pick=[None]*(size*size)
        textures={'top':top,'bottom':bottom,'side':side}
        textures={k:v.convert('RGBA').resize((64,64),Image.Resampling.NEAREST) for k,v in textures.items()}
        c,s=math.cos(self.view_yaw),math.sin(self.view_yaw)
        cp,sp=math.cos(self.view_pitch),math.sin(self.view_pitch)
        def project(v):
            x,y,z=v
            x,z=c*x+s*z,-s*x+c*z
            y,z=cp*y-sp*z,sp*y+cp*z
            depth=z+3.8
            scale=(size*125/216)*self.view_zoom/depth
            return (size/2+x*scale,size/2-y*scale,depth)
        verts=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
               (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
        faces3=[
            ([3,2,6,7],'top',1.0),
            ([0,4,5,1],'bottom',0.60),
            ([4,7,6,5],'side',0.88),
            ([1,2,3,0],'side',0.70),
            ([0,3,7,4],'side',0.78),
            ([5,6,2,1],'side',0.83),
        ]
        model_quads=entity_quads or self.model_geometry()
        coords=[project(v) for v in verts]
        def raster(tri,uvs,texture,brightness,path):
            (ax,ay,az),(bx,by,bz),(cx,cy,cz)=tri
            area=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
            if abs(area)<1e-6:return
            x0=max(0,int(math.floor(min(ax,bx,cx))))
            x1=min(size-1,int(math.ceil(max(ax,bx,cx))))
            y0=max(0,int(math.floor(min(ay,by,cy))))
            y1=min(size-1,int(math.ceil(max(ay,by,cy))))
            tpx=texture.load()
            texture_width,texture_height=texture.size
            for py in range(y0,y1+1):
                for px in range(x0,x1+1):
                    x=px+0.5;y=py+0.5
                    w1=((x-ax)*(cy-ay)-(y-ay)*(cx-ax))/area
                    w2=((bx-ax)*(y-ay)-(by-ay)*(x-ax))/area
                    w0=1-w1-w2
                    if min(w0,w1,w2)<-0.0001:continue
                    invz=w0/az+w1/bz+w2/cz
                    if invz<=0:continue
                    depth=1/invz
                    idx=py*size+px
                    if depth>=zbuf[idx]:continue
                    u=(w0*uvs[0][0]/az+w1*uvs[1][0]/bz+w2*uvs[2][0]/cz)*depth
                    v=(w0*uvs[0][1]/az+w1*uvs[1][1]/bz+w2*uvs[2][1]/cz)*depth
                    tx=max(0,min(texture_width-1,int(u*texture_width)))
                    ty=max(0,min(texture_height-1,int(v*texture_height)))
                    r,g,b,a=tpx[tx,ty]
                    if a==0:continue
                    zbuf[idx]=depth
                    pick[idx]=path
                    pixels[px,py]=(int(r*brightness),int(g*brightness),int(b*brightness),a)
        if model_quads:
            for quad,uv,texpath,shade in model_quads:
                tex=self.composite_layers() if texpath==self.current else self.image_for(texpath)
                if texpath not in self.base and texpath not in self.edits and texpath not in self.names:continue
                tex=tex.convert('RGBA') if entity_quads else tex.convert('RGBA').resize((64,64),Image.Resampling.NEAREST)
                v=[project(point) for point in quad]
                raster([v[0],v[1],v[2]],[uv[0],uv[1],uv[2]],tex,shade,texpath)
                raster([v[0],v[2],v[3]],[uv[0],uv[2],uv[3]],tex,shade,texpath)
        else:
            for indices,kind,shade in faces3:
                v=[coords[i] for i in indices]
                uv=[(0,1),(0,0),(1,0),(1,1)]
                raster([v[0],v[1],v[2]],[uv[0],uv[1],uv[2]],textures[kind],shade,mapped.get({'top':'Top','bottom':'Bottom','side':'Side'}[kind],self.current))
                raster([v[0],v[2],v[3]],[uv[0],uv[2],uv[3]],textures[kind],shade,mapped.get({'top':'Top','bottom':'Bottom','side':'Side'}[kind],self.current))
        self.preview_photo=ImageTk.PhotoImage(out)
        if size==216:self.block_preview.create_image(108,102,image=self.preview_photo)
        if size!=216:
            self.preview_small_photo=ImageTk.PhotoImage(out.resize((216,216),Image.Resampling.NEAREST))
            self.block_preview.delete('all')
            self.block_preview.create_image(108,102,image=self.preview_small_photo)
        if full:
            canvas=self.fullscreen_canvas
            self.preview_pick=pick if not self.preview_interactive else None
            self.preview_pick_size=size
            self.preview_pick_offset=(canvas.winfo_width()//2-size//2,canvas.winfo_height()//2-size//2)
            canvas.delete('all')
            # Keep the preview the same on-screen size during fast rotation.
            display=out.resize((target_size,target_size),Image.Resampling.NEAREST) if size!=target_size else out
            self.fullscreen_photo=ImageTk.PhotoImage(display)
            canvas.create_image(canvas.winfo_width()//2,canvas.winfo_height()//2,image=self.fullscreen_photo)

    def new_texture(self):
        p=simpledialog.askstring('New texture','Enter a texture path, e.g. block/custom_stone or gui/sprites/widget/button',parent=self.root)
        if p is None:return
        p=p.strip().lower().removesuffix('.png')
        if not self.valid(p):messagebox.showerror('Invalid path','Use block/..., item/..., gui/... etc. (lowercase).');return
        self.open_path(p)
        self.show_editor()

    def import_asset_zip(self, f, notify=True, remember=True):
        found={}
        other={}
        detected_pack_format=None
        with zipfile.ZipFile(f) as z:
            # Read version-specific metadata from the selected client JAR itself.
            # Do not guess a pack_format from a Minecraft release number.
            if 'pack.mcmeta' in z.namelist():
                try:
                    metadata=json.loads(z.read('pack.mcmeta').decode('utf-8'))
                    candidate=metadata.get('pack',{}).get('pack_format')
                    if isinstance(candidate,int) and candidate>0:
                        detected_pack_format=candidate
                except (ValueError,UnicodeDecodeError,TypeError):pass
            for entry in z.infolist():
                if entry.filename.startswith('assets/minecraft/') and not entry.is_dir() and not entry.filename.endswith('.png') and entry.file_size < 12_000_000 and '..' not in entry.filename.split('/'):
                    if entry.filename.endswith(('.json','.lang','.ogg','.fsh','.vsh','.glsl','.mcmeta')):other[entry.filename]=z.read(entry)
                name=entry.filename.replace('\\\\','/')
                pos=name.find(PREFIX)
                if pos>=0 and name.endswith('.png') and not entry.is_dir():
                    key=name[pos+len(PREFIX):-4]
                    if self.valid(key) and entry.file_size<12_000_000:
                        data=z.read(entry)
                        try:
                            with Image.open(io.BytesIO(data)) as im:im.verify()
                            found[key]=data
                        except Exception:pass
        if not found:
            raise ValueError('No assets/minecraft/textures/*.png found. Select a Minecraft Java client JAR, not a mod loader or server JAR.')
        self.save(silent=True)
        self.base=found
        self.minecraft_version.set(Path(f).stem if Path(f).suffix.lower()=='.jar' else 'Custom ZIP')
        if detected_pack_format is not None:
            self.format.set(str(detected_pack_format))
        self.other_assets=other
        self.other_base=other.copy()
        self.modified_other.clear()
        self.names.update(found)
        self.refresh_list()
        self.open_path(self.current)
        self.status.set(f'Loaded {len(found):,} textures from {os.path.basename(f)}. Minecraft: {self.minecraft_version.get()}. '+
                        (f'JAR pack_format detected: {detected_pack_format}.' if detected_pack_format else 'Pack format must be verified manually.'))
        if remember:self.remember_assets('jar',f)
        if notify:messagebox.showinfo('Assets loaded',f'Loaded {len(found):,} textures.\\n\\nUse the category selector on the left to browse GUI, items, entities, particles and blocks.')

    def find_minecraft(self):
        candidates=[]
        home=Path.home()
        for base in [Path(os.environ.get('APPDATA',''))/'.minecraft',home/'.minecraft',home/'AppData/Roaming/.minecraft']:
            versions=base/'versions'
            if versions.is_dir():
                for jar in versions.glob('*/*.jar'):
                    if jar.stem==jar.parent.name:
                        candidates.append(jar)
        if not candidates:
            messagebox.showinfo('Minecraft not found','No standard Minecraft Java installation found. Open Minecraft Java Edition once in the launcher, then click Load Minecraft .jar / assets ZIP and select a version JAR from .minecraft/versions.')
            return
        candidates.sort(key=lambda f:f.stat().st_mtime,reverse=True)
        errors=[]
        for jar in candidates:
            try:
                self.import_asset_zip(jar,notify=False)
                self.status.set(f'Loaded Minecraft textures from {jar.name}. This path will be remembered.')
                return
            except Exception as exc:
                errors.append(f'{jar.name}: {exc}')
        messagebox.showerror('Could not load textures',
            'Minecraft version files were found, but none contained usable textures.\n\n'
            'Choose the official Minecraft Java client JAR using Load JAR / ZIP.\n\n'
            'First error: '+(errors[0] if errors else 'Unknown error'))

    def load_folder(self):
        folder=filedialog.askdirectory(title='Select a folder containing assets/minecraft/textures')
        if not folder:return
        try:self.import_asset_folder(folder)
        except Exception as exc:messagebox.showerror('Could not load assets folder',str(exc))

    def import_asset_folder(self,folder,remember=True):
        base=Path(folder)
        root=base/'assets/minecraft/textures'
        if not root.is_dir() and (base/'minecraft/textures').is_dir():root=base/'minecraft/textures'
        if not root.is_dir() and (base/'textures').is_dir():root=base/'textures'
        if not root.is_dir():root=base
        found={}
        for f in root.rglob('*.png'):
            if not f.is_file() or f.stat().st_size>=12_000_000:continue
            key=f.relative_to(root).as_posix()[:-4]
            if self.valid(key):found[key]=f.read_bytes()
        if not found:
            raise ValueError('No valid PNG textures in saved assets folder')
        self.save(silent=True)
        self.base=found;self.minecraft_version.set('Custom assets folder');self.names.update(found)
        self.other_assets={}
        self.modified_other.clear()
        for f in base.rglob('*'):
            if f.is_file() and f.suffix.lower() in ('.json','.lang','.ogg','.fsh','.vsh','.glsl','.mcmeta') and f.stat().st_size<12_000_000:
                rel=f.relative_to(base).as_posix()
                if rel.startswith('assets/minecraft/') and '..' not in rel.split('/'):
                    self.other_assets[rel]=f.read_bytes()
        self.other_base=self.other_assets.copy()
        self.refresh_list();self.open_path(self.current)
        self.status.set(f'Loaded {len(found):,} textures from folder.')
        if remember:self.remember_assets('folder',folder)

    def load_vanilla(self):
        f=filedialog.askopenfilename(title='Choose Minecraft Java client .jar or assets .zip',filetypes=[('Minecraft JAR or ZIP','*.jar *.zip'),('All files','*.*')])
        if not f:return
        try:self.import_asset_zip(f)
        except Exception as ex:messagebox.showerror('Could not load assets',str(ex))

    def save(self,silent=False):
        self.sync_layer()
        if self.dirty or self.current in self.edits:
            self.layer_docs[self.current]=[{'name':a['name'],'visible':a['visible'],'image':a['image'].copy()} for a in self.layers]
        if self.dirty or self.current in self.edits:
            self.edits[self.current]=self.composite_layers()
        self.dirty=False;self.refresh_list()
        if not silent:self.status.set('Saved '+self.current)

    def checkpoint(self):
        self.history.append(self.image.copy())
        if len(self.history)>40:self.history.pop(0)
        self.redo_stack.clear();self.dirty=True

    def undo(self):
        if self.history:self.redo_stack.append(self.image.copy());self.image=self.history.pop();self.draw()
    def redo(self):
        if self.redo_stack:self.history.append(self.image.copy());self.image=self.redo_stack.pop();self.draw()

    def layout(self):
        w,h=self.image.size
        cw=max(self.canvas.winfo_width(),100);ch=max(self.canvas.winfo_height(),100)
        z=max(1,min(32,(cw-28)//w,(ch-28)//h))
        z=getattr(self,'zoom_override',z)
        self.zoom=z
        return (cw-w*z)//2,(ch-h*z)//2,z

    def draw(self):
        if not hasattr(self,'canvas'):return
        self.canvas.delete('all')
        ox,oy,z=self.layout();w,h=self.image.size
        checker=Image.new('RGBA',(w,h))
        d=ImageDraw.Draw(checker)
        for y in range(h):
            for x in range(w):d.point((x,y),fill='#b8bfcb' if (x//4+y//4)%2 else '#e6e9ef')
        checker.alpha_composite(self.composite_layers())
        if self.drag_image is not None and self.selection and self.tool.get()=='Move':
            x0,y0,x1,y1=self.selection;dx,dy=self.preview_offset
            tmp=checker.copy()
            # Preview floating pixels over the unmodified original; release commits the move.
            tmp.alpha_composite(self.drag_image,(x0+dx,y0+dy)) if x0+dx>=0 and y0+dy>=0 and x1+dx<=w and y1+dy<=h else None
            checker=tmp
        scaled=checker.resize((w*z,h*z),Image.Resampling.NEAREST)
        self.photo=ImageTk.PhotoImage(scaled)
        self.canvas.create_image(ox,oy,image=self.photo,anchor='nw')
        if self.grid_on.get() and z>=7:
            for x in range(w+1):self.canvas.create_line(ox+x*z,oy,ox+x*z,oy+h*z,fill='#566074',width=1)
            for y in range(h+1):self.canvas.create_line(ox,oy+y*z,ox+w*z,oy+y*z,fill='#566074',width=1)
        self.schedule_preview()
        if self.selection:
            x0,y0,x1,y1=self.selection
            dx,dy=self.preview_offset if self.drag_image is not None else (0,0)
            self.canvas.create_rectangle(ox+(x0+dx)*z,oy+(y0+dy)*z,ox+(x1+dx)*z,oy+(y1+dy)*z,outline='#ffda70',width=2,dash=(5,3))

    def coords(self,e):
        ox,oy,z=self.layout()
        return (e.x-ox)//z,(e.y-oy)//z

    def in_bounds(self,x,y):return 0<=x<self.image.width and 0<=y<self.image.height
    def paint(self,x,y):
        if self.in_bounds(x,y):
            self.image.putpixel((x,y),(0,0,0,0) if self.tool.get()=='Eraser' else self.color)
            self.draw()

    def flood_fill(self,x,y):
        old=self.image.getpixel((x,y))
        new=self.color
        if old==new:return
        w,h=self.image.size
        pixels=self.image.load()
        stack=[(x,y)]
        while stack:
            px,py=stack.pop()
            if px<0 or py<0 or px>=w or py>=h or pixels[px,py]!=old:continue
            pixels[px,py]=new
            stack.extend(((px-1,py),(px+1,py),(px,py-1),(px,py+1)))
        self.dirty=True
        self.draw()

    def transform_selection(self,kind):
        if not self.selection:
            messagebox.showinfo('Select an area','Drag to select pixels first.')
            return
        self.checkpoint()
        box=self.selection
        patch=self.image.crop(box)
        if kind=='flip_h':patch=patch.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        elif kind=='flip_v':patch=patch.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        elif kind=='rotate':
            patch=patch.transpose(Image.Transpose.ROTATE_270)
            if patch.size!=(box[2]-box[0],box[3]-box[1]):
                patch=patch.resize((box[2]-box[0],box[3]-box[1]),Image.Resampling.NEAREST)
        self.image.paste(patch,box[:2])
        self.dirty=True
        self.draw()

    def install_resource_pack(self):
        source=filedialog.askopenfilename(title='Select an exported resource pack ZIP',filetypes=[('ZIP resource pack','*.zip')])
        if not source:return
        try:
            with zipfile.ZipFile(source) as z:
                if 'pack.mcmeta' not in z.namelist():raise ValueError('ZIP has no pack.mcmeta')
                json.loads(z.read('pack.mcmeta').decode('utf-8'))
            minecraft=Path(os.environ.get('APPDATA',str(Path.home()/'AppData/Roaming')))/'.minecraft'
            if not minecraft.is_dir():
                minecraft=Path.home()/'.minecraft'
            if not minecraft.is_dir():
                messagebox.showerror('Minecraft folder not found','Install or launch Minecraft Java Edition first.')
                return
            target=minecraft/'resourcepacks'
            target.mkdir(parents=True,exist_ok=True)
            destination=target/Path(source).name
            if destination.exists() and not messagebox.askyesno('Overwrite pack?',f'Replace {destination.name}?'):return
            shutil.copy2(source,destination)
            messagebox.showinfo('Copied','Resource pack copied to:\\n'+str(destination)+'\\n\\nOpen Minecraft Resource Packs settings to activate it.')
        except Exception as ex:messagebox.showerror('Copy failed',str(ex))

    def mouse_down(self,e):
        x,y=self.coords(e);self.anchor=(x,y)
        tool=self.tool.get()
        if tool=='Eyedropper':
            if self.in_bounds(x,y):self.color=self.image.getpixel((x,y));self.status.set('Color sampled: '+str(self.color))
        elif tool=='Fill':
            if self.in_bounds(x,y):
                self.checkpoint()
                self.flood_fill(x,y)
        elif tool in ('Pencil','Eraser'):
            if self.in_bounds(x,y):self.checkpoint();self.paint(x,y)
        elif tool in ('Line','Rectangle'):
            if self.in_bounds(x,y):
                self.checkpoint()
                self.shape_start=(x,y)
                self.shape_base=self.image.copy()
        elif tool=='Select':
            self.selection=(max(0,min(x,self.image.width-1)),max(0,min(y,self.image.height-1)),max(0,min(x,self.image.width-1))+1,max(0,min(y,self.image.height-1))+1);self.draw()
        elif tool=='Move' and self.selection:
            x0,y0,x1,y1=self.selection
            if x0<=x<x1 and y0<=y<y1:
                self.drag_origin=(x,y)
                self.drag_image=self.image.crop(self.selection)
                self.preview_offset=(0,0)

    def mouse_drag(self,e):
        x,y=self.coords(e);tool=self.tool.get()
        if tool in ('Pencil','Eraser'):
            if self.anchor:
                ax,ay=self.anchor
                steps=max(abs(x-ax),abs(y-ay),1)
                for i in range(steps+1):
                    px=round(ax+(x-ax)*i/steps);py=round(ay+(y-ay)*i/steps)
                    if self.in_bounds(px,py):self.image.putpixel((px,py),(0,0,0,0) if tool=='Eraser' else self.color)
                self.anchor=(x,y);self.draw()
        elif tool in ('Line','Rectangle') and getattr(self,'shape_start',None) is not None:
            self.render_shape(x,y)
        elif tool=='Select' and self.anchor:
            ax,ay=self.anchor
            x0=max(0,min(ax,x));y0=max(0,min(ay,y));x1=min(self.image.width,max(ax,x)+1);y1=min(self.image.height,max(ay,y)+1)
            if x0<x1 and y0<y1:self.selection=(x0,y0,x1,y1);self.draw()
        elif tool=='Move' and self.drag_origin:
            dx=x-self.drag_origin[0];dy=y-self.drag_origin[1]
            x0,y0,x1,y1=self.selection
            dx=max(-x0,min(dx,self.image.width-x1));dy=max(-y0,min(dy,self.image.height-y1))
            self.preview_offset=(dx,dy);self.draw()

    def render_shape(self,x,y):
        if self.shape_base is None:return
        self.image=self.shape_base.copy()
        ax,ay=self.shape_start
        x=max(0,min(self.image.width-1,x))
        y=max(0,min(self.image.height-1,y))
        draw=ImageDraw.Draw(self.image)
        if self.tool.get()=='Line':
            draw.line((ax,ay,x,y),fill=self.color,width=1)
        else:
            draw.rectangle((min(ax,x),min(ay,y),max(ax,x),max(ay,y)),outline=self.color,width=1)
        self.draw()

    def mouse_up(self,e):
        if getattr(self,'shape_start',None) is not None:
            x,y=self.coords(e)
            self.render_shape(x,y)
            self.shape_start=None
            self.shape_base=None
            self.dirty=True
        if self.drag_image is not None and self.selection:
            dx,dy=self.preview_offset
            if dx or dy:
                self.checkpoint();x0,y0,x1,y1=self.selection
                self.image.paste((0,0,0,0),(x0,y0,x1,y1))
                self.image.alpha_composite(self.drag_image,(x0+dx,y0+dy))
                self.selection=(x0+dx,y0+dy,x1+dx,y1+dy)
            self.drag_image=None;self.preview_offset=(0,0);self.drag_origin=None;self.draw()
        self.anchor=None

    def mouse_wheel(self,e):
        self.editor_zoom(1.25 if e.delta>0 else 0.8)

    def select_all(self):self.selection=(0,0,*self.image.size);self.tool.set('Select');self.draw()
    def clear_selection(self):self.selection=None;self.draw()
    def copy_selection(self):
        if not self.selection:self.status.set('Select an area first.');return
        self.clipboard=self.image.crop(self.selection);self.status.set('Selection copied.')
    def cut_selection(self):
        if not self.selection:return
        self.copy_selection();self.delete_selection()
    def delete_selection(self):
        if not self.selection:return
        self.checkpoint();self.image.paste((0,0,0,0),self.selection);self.draw()
    def paste_selection(self):
        if self.clipboard is None:return
        self.checkpoint()
        x,y=(self.selection[:2] if self.selection else (0,0))
        layer=Image.new('RGBA',self.image.size,(0,0,0,0));layer.paste(self.clipboard,(x,y))
        self.image=Image.alpha_composite(self.image,layer)
        self.selection=(x,y,min(self.image.width,x+self.clipboard.width),min(self.image.height,y+self.clipboard.height))
        self.tool.set('Move');self.draw()
    def crop_selection(self):
        if not self.selection:return
        self.checkpoint();self.image=self.image.crop(self.selection);self.resize_other_layers(self.image.size, crop=self.selection);self.selection=None;self.path_label.config(text=self.current+'  —  '+str(self.image.width)+' × '+str(self.image.height));self.draw()
    def resize_image(self):
        w=simpledialog.askinteger('Resize','Width (pixels):',initialvalue=self.image.width,minvalue=1,maxvalue=1024,parent=self.root)
        if w is None:return
        h=simpledialog.askinteger('Resize','Height (pixels):',initialvalue=self.image.height,minvalue=1,maxvalue=1024,parent=self.root)
        if h is None:return
        self.checkpoint();self.image=self.image.resize((w,h),Image.Resampling.NEAREST);self.resize_other_layers((w,h));self.selection=None;self.path_label.config(text=f'{self.current}  —  {w} × {h}');self.draw()
    def clear_image(self):
        self.checkpoint();self.image=Image.new('RGBA',self.image.size,(0,0,0,0));self.draw()
    def choose_color(self):
        result=colorchooser.askcolor(color='#%02x%02x%02x'%self.color[:3],parent=self.root)
        if result[0]:self.color=tuple(round(c) for c in result[0])+(255,);self.tool.set('Pencil')
    def import_png(self):
        f=filedialog.askopenfilename(filetypes=[('PNG image','*.png')])
        if not f:return
        try:
            with Image.open(f) as im:
                if im.width>1024 or im.height>1024:raise ValueError('Maximum texture size is 1024×1024.')
                self.checkpoint();self.image=im.convert('RGBA').copy()
            self.resize_other_layers(self.image.size);self.selection=None;self.path_label.config(text=f'{self.current}  —  {self.image.width} × {self.image.height}');self.draw()
        except Exception as ex:messagebox.showerror('PNG import failed',str(ex))
    def asset_manager(self):
        win=tk.Toplevel(self.root);win.title('Other Minecraft Assets — JSON / Sounds');win.geometry('900x650')
        left=ttk.Frame(win,padding=8);left.pack(side='left',fill='y')
        right=ttk.Frame(win,padding=8);right.pack(side='left',fill='both',expand=True)
        query=tk.StringVar()
        ttk.Entry(left,textvariable=query,width=42).pack(fill='x')
        lb=tk.Listbox(left,width=48,exportselection=False);lb.pack(fill='both',expand=True)
        editor=tk.Text(right,wrap='none',undo=True,font=('Consolas',10));editor.pack(fill='both',expand=True)
        current=[None]
        def refresh(*_):
            lb.delete(0,'end')
            for name in sorted(self.other_assets):
                if query.get().lower() in name.lower():lb.insert('end',name)
        def choose(_=None):
            sel=lb.curselection()
            if not sel:return
            name=lb.get(sel[0]);current[0]=name;editor.delete('1.0','end')
            data=self.other_assets[name]
            if name.endswith('.ogg'):
                editor.insert('1.0',f'OGG audio: {len(data):,} bytes\nUse Replace File to change this sound.');editor.config(state='disabled')
            else:
                editor.config(state='normal');editor.insert('1.0',data.decode('utf-8',errors='replace'))
        def save_text():
            name=current[0]
            if not name or name.endswith('.ogg'):return
            value=editor.get('1.0','end-1c')
            if name.endswith('.json'):
                try:json.loads(value)
                except Exception as ex:
                    messagebox.showerror('Invalid JSON',str(ex),parent=win);return
            self.other_assets[name]=value.encode('utf-8')
            self.modified_other.add(name)
            self.status.set('Saved '+name)
        def replace_file():
            name=current[0]
            if not name:return
            f=filedialog.askopenfilename(parent=win)
            if not f:return
            data=Path(f).read_bytes()
            if len(data)>12_000_000:messagebox.showerror('Too large','12 MB maximum',parent=win);return
            self.other_assets[name]=data;self.modified_other.add(name);choose()
        def add_file():
            name=simpledialog.askstring('Asset path','Path, e.g. assets/minecraft/lang/en_us.json',parent=win)
            if not name:return
            name=name.replace('\\','/')
            if not name.startswith('assets/minecraft/') or '..' in name.split('/') or not name.endswith(('.json','.lang','.ogg','.fsh','.vsh','.glsl','.mcmeta')):
                messagebox.showerror('Invalid path','Use assets/minecraft/... with a supported file extension',parent=win);return
            self.other_assets.setdefault(name,b'{}' if name.endswith('.json') else b'')
            self.modified_other.add(name)
            refresh()
        query.trace_add('write',refresh);lb.bind('<<ListboxSelect>>',choose)
        bar=ttk.Frame(right);bar.pack(fill='x')
        for title,fn in [('Save Text',save_text),('Replace File',replace_file),('Add Asset',add_file)]:ttk.Button(bar,text=title,command=fn).pack(side='left',padx=4)
        ttk.Label(right,text='JSON models, language files, shaders and sounds. Sound editing = file replacement only.').pack(anchor='w')
        refresh()

    def save_project(self):
        self.save(silent=True)
        f=filedialog.asksaveasfilename(defaultextension='.prism',filetypes=[('MC Resource Table project','*.prism')],initialfile='My_MC_Project.prism')
        if not f:return
        try:
            self.write_project(Path(f))
            self.project_file=f
            self.status.set('Project saved: '+f)
        except Exception as ex:messagebox.showerror('Project save failed',str(ex))

    def write_project(self, target):
        target=Path(target)
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_suffix('.tmp')
        try:
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
                manifest={'version':1,'pack_name':self.pack_name.get(),'pack_format':self.format.get(),'minecraft_version':self.minecraft_version.get(),'current':self.current,'layers':{}}
                for i,(path,layers) in enumerate(self.layer_docs.items()):
                    manifest['layers'][path]=[]
                    for j,layer in enumerate(layers):
                        filename=f'layers/{i}_{j}.png';data=io.BytesIO();layer['image'].save(data,format='PNG');z.writestr(filename,data.getvalue())
                        manifest['layers'][path].append({'name':layer['name'],'visible':layer['visible'],'file':filename})
                for i,(path,im) in enumerate(self.edits.items()):
                    data=io.BytesIO();im.save(data,format='PNG');filename=f'edits/{i}.png';z.writestr(filename,data.getvalue());manifest.setdefault('edits',{})[path]=filename
                for i,path in enumerate(sorted(self.modified_other)):
                    data=self.other_assets[path]
                    filename=f'other/{i}';z.writestr(filename,data);manifest.setdefault('other',{})[path]=filename
                z.writestr('project.json',json.dumps(manifest))
            temp.replace(target)
        finally:
            if temp.exists():temp.unlink()

    def autosave_tick(self):
        try:
            self.save(silent=True)
            if self.edits or self.modified_other:
                self.write_project(self.autosave_path)
        except Exception as exc:
            self.status.set('Autosave failed: '+str(exc))
        finally:
            self.root.after(60000,self.autosave_tick)

    def offer_recovery(self):
        if self.autosave_path.is_file() and messagebox.askyesno('Recover unsaved work','A recovery project exists. Open it?'):
            self.read_project(self.autosave_path)

    def show_validation(self):
        self.save(silent=True)
        issues=self.validate_pack()
        if issues:messagebox.showwarning('Validation issues','\n'.join(issues[:20]))
        else:messagebox.showinfo('Validation','No basic structural errors found. In-game compatibility is NOT guaranteed. Confirm pack format for your target Minecraft version.')

    def open_project(self):
        f=filedialog.askopenfilename(filetypes=[('Prism project','*.prism')])
        if not f:return
        self.read_project(f)

    def read_project(self,f):
        try:
            with zipfile.ZipFile(f) as z:
                manifest=json.loads(z.read('project.json'))
                if manifest.get('version')!=1:raise ValueError('Unsupported project format')
                def image_at(name):
                    with Image.open(io.BytesIO(z.read(name))) as im:return im.convert('RGBA').copy()
                docs={}
                for path,layers in manifest.get('layers',{}).items():
                    if self.valid(path):docs[path]=[{'name':v['name'],'visible':v['visible'],'image':image_at(v['file'])} for v in layers]
                edits={path:image_at(filename) for path,filename in manifest.get('edits',{}).items() if self.valid(path)}
                others={path:z.read(filename) for path,filename in manifest.get('other',{}).items() if path.startswith('assets/minecraft/') and '..' not in path.split('/')}
            self.layer_docs=docs;self.edits=edits;self.other_assets={**self.other_base,**others};self.modified_other=set(others);self.names.update(docs);self.names.update(edits)
            self.pack_name.set(manifest.get('pack_name','My MC Resource Pack'));self.format.set(manifest.get('pack_format','15'));self.minecraft_version.set(manifest.get('minecraft_version','Unknown'))
            self.open_path(manifest.get('current','block/stone'),initial=True)
            self.project_file=str(f);self.status.set('Project opened: '+str(f))
        except Exception as ex:messagebox.showerror('Project open failed',str(ex))

    def validate_pack(self):
        issues=[]
        if not self.edits and not self.modified_other:
            issues.append('No edited assets to export.')
        if not self.pack_name.get().strip():
            issues.append('Pack description is empty.')
        for path in sorted(self.modified_other):
            if path.endswith('.json'):
                try:json.loads(self.other_assets[path].decode('utf-8'))
                except Exception as exc:issues.append(f'Invalid JSON {path}: {exc}')
            if path.endswith('.ogg') and not self.other_assets[path].startswith(b'OggS'):
                issues.append(f'Invalid OGG header: {path}')
        for path,im in self.edits.items():
            if im.width<1 or im.height<1 or im.width>4096 or im.height>4096:
                issues.append(f'Unsupported texture dimensions: {path}')
        return issues

    def export(self):
        self.save(silent=True)
        try:
            fmt=int(self.format.get());assert fmt>0
        except (ValueError,AssertionError):messagebox.showerror('Invalid pack format','Enter a positive pack_format integer for your target Minecraft version.');return
        issues=self.validate_pack()
        if issues:
            messagebox.showerror('Pack validation failed','Fix these issues before exporting:\\n\\n'+'\\n'.join(issues[:15]))
            return
        if not messagebox.askyesno('Confirm Minecraft version',f'Target Minecraft: {self.minecraft_version.get()}\npack_format: {fmt}\n\nThis tool cannot confirm the latest release metadata automatically. Have you verified the pack format matches your installed game?'):
            return
        f=filedialog.asksaveasfilename(defaultextension='.zip',filetypes=[('Minecraft resource pack','*.zip')],initialfile='MC_Resource_Table_Pack.zip')
        if not f:return
        try:
            with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':fmt,'description':self.pack_name.get()}},indent=2))
                for path in sorted(self.modified_other):
                    data=self.other_assets[path]
                    if path.startswith('assets/minecraft/') and '..' not in path.split('/'):
                        z.writestr(path,data)
                for p,im in self.edits.items():
                    if not self.valid(p):continue
                    data=io.BytesIO();im.save(data,format='PNG')
                    z.writestr(PREFIX+p+'.png',data.getvalue())
            self.status.set(f'Exported {len(self.edits)} edited texture(s): {f}')
            messagebox.showinfo('Resource pack exported','ZIP created. Put it in your Minecraft resourcepacks folder.\n\nOnly edited textures and modified other assets are included.')
        except Exception as ex:messagebox.showerror('Export failed',str(ex))

if __name__=='__main__':
    root=tk.Tk();Studio(root);root.mainloop()

