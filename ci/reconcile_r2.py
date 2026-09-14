#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys, zipfile

PAYLOAD='25220886837b724f781612f66ae5f8fd4a983ca644559c4871aff91b479e24b7'
LAUNCHER='dbd00a8d0e8ce09574c9c730b5fb4fa0049b3470171204c6db4712184bb54f7e'

def sha(p: Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(cond, msg):
    if not cond: raise SystemExit(msg)

def patch(root: Path):
    require(sha(root/'academic_payload/index.html') == PAYLOAD, 'academic payload hash mismatch before patch')
    require(sha(root/'app/src/main/assets/www/index.html') == PAYLOAD, 'Android payload copy hash mismatch before patch')
    require(sha(root/'launcher_assets/master/invertebrata_icon_master.png') == LAUNCHER, 'launcher hash mismatch before patch')

    p=root/'app/src/main/java/com/gasczoology/invertebratelab/MainActivity.java'
    s=p.read_text(encoding='utf-8')
    replacements=[
      ('import android.app.Activity;\n',''),
      ('import android.window.OnBackInvokedCallback;\nimport android.window.OnBackInvokedDispatcher;\n',''),
      ('import androidx.webkit.WebViewAssetLoader;\n','import androidx.activity.ComponentActivity;\nimport androidx.activity.OnBackPressedCallback;\nimport androidx.webkit.WebViewAssetLoader;\n'),
      ('public class MainActivity extends Activity {','public class MainActivity extends ComponentActivity {'),
      ('    private OnBackInvokedCallback backCallback;\n',''),
      ('        createWebView(savedInstanceState);\n        registerPredictiveBack();\n','        createWebView(savedInstanceState);\n        registerBackNavigation();\n'),
      ('''        getWindow().getDecorView().setSystemUiVisibility(\n                View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);\n''','''        int systemUiFlags = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {\n            systemUiFlags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;\n        }\n        getWindow().getDecorView().setSystemUiVisibility(systemUiFlags);\n'''),
      ('''    private void registerPredictiveBack() {\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {\n            backCallback = this::handleBack;\n            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(\n                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, backCallback);\n        }\n    }\n''','''    private void registerBackNavigation() {\n        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {\n            @Override\n            public void handleOnBackPressed() {\n                handleBack();\n            }\n        });\n    }\n'''),
      ('''    @Override\n    @SuppressWarnings("deprecation")\n    public void onBackPressed() {\n        handleBack();\n    }\n\n''',''),
      ('''    @Override\n    protected void onDestroy() {\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && backCallback != null) {\n            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backCallback);\n            backCallback = null;\n        }\n        destroyWebView();\n        super.onDestroy();\n    }\n''','''    @Override\n    protected void onDestroy() {\n        destroyWebView();\n        super.onDestroy();\n    }\n''')]
    for old,new in replacements:
        require(old in s, 'expected MainActivity source fragment not found; refusing non-deterministic patch')
        s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8',newline='\n')

    b=root/'app/build.gradle'; t=b.read_text(encoding='utf-8')
    old="dependencies {\n    implementation 'androidx.webkit:webkit:1.17.0'\n}"
    new="dependencies {\n    implementation 'androidx.activity:activity:1.11.0'\n    implementation 'androidx.webkit:webkit:1.17.0'\n}"
    require(old in t,'expected Gradle dependency block not found')
    b.write_text(t.replace(old,new,1),encoding='utf-8',newline='\n')

    st=root/'app/src/main/res/values/styles.xml'; u=st.read_text(encoding='utf-8')
    attr='        <item name="android:windowLightNavigationBar">true</item>\n'
    require(attr in u,'expected windowLightNavigationBar theme item not found')
    st.write_text(u.replace(attr,'',1),encoding='utf-8',newline='\n')
    v27=root/'app/src/main/res/values-v27'; v27.mkdir(parents=True,exist_ok=True)
    (v27/'styles.xml').write_text('<resources>\n    <style name="AppTheme">\n        <item name="android:windowLightNavigationBar">true</item>\n    </style>\n</resources>\n',encoding='utf-8',newline='\n')

    report=root/'provenance/R2_ANDROID_SHELL_RECONCILIATION.md'
    report.write_text('''# INVERTEBRATA v1.8.7 — R2 Android shell reconciliation\n\nDerived deterministically from the frozen reconciled source whose ZIP SHA-256 is `281e5f80a14f80df6ad87427a8e29859050f35430ec3158ad52b84ae607df1a3`.\n\nCorrections are limited to Android-shell compatibility defects exposed by genuine Android 16 / API 36 lint:\n\n- Migrated Back handling from `Activity.onBackPressed()` / platform callback wiring to AndroidX `OnBackPressedDispatcher` through `ComponentActivity`.\n- Added `androidx.activity:activity:1.11.0`, a stable Activity release compiled with API 36.\n- Moved `android:windowLightNavigationBar` from the base values theme to `values-v27`, matching its API requirement.\n- Guarded the API 26 `SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR` flag at runtime.\n\nThe academic payload is intentionally unchanged. Both `academic_payload/index.html` and `app/src/main/assets/www/index.html` remain SHA-256 `25220886837b724f781612f66ae5f8fd4a983ca644559c4871aff91b479e24b7`. The launcher master remains SHA-256 `dbd00a8d0e8ce09574c9c730b5fb4fa0049b3470171204c6db4712184bb54f7e`.\n''',encoding='utf-8',newline='\n')

    mf=root/'provenance/SOURCE_MANIFEST_SHA256.txt'
    tracked=[]
    for line in mf.read_text(encoding='utf-8').splitlines():
        if line.strip(): tracked.append(line.split('  ',1)[1])
    for new_rel in ['app/src/main/res/values-v27/styles.xml','provenance/R2_ANDROID_SHELL_RECONCILIATION.md']:
        if new_rel not in tracked: tracked.append(new_rel)
    lines=[]
    for rel in sorted(tracked):
        fp=root/rel; require(fp.is_file(),f'missing tracked file after patch: {rel}')
        lines.append(f'{sha(fp)}  {rel}')
    mf.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')

    require(sha(root/'academic_payload/index.html') == PAYLOAD, 'academic payload changed')
    require(sha(root/'app/src/main/assets/www/index.html') == PAYLOAD, 'Android payload copy changed')
    require(sha(root/'launcher_assets/master/invertebrata_icon_master.png') == LAUNCHER, 'launcher master changed')

def deterministic_zip(root: Path, out: Path):
    epoch=(2026,9,14,10,0,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for fp in sorted(p for p in root.rglob('*') if p.is_file()):
            rel=(Path(root.name)/fp.relative_to(root)).as_posix()
            info=zipfile.ZipInfo(rel,date_time=epoch)
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=(0o100644 << 16)
            z.writestr(info,fp.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: reconcile_r2.py EXTRACTED_ROOT OUTPUT_ZIP')
    root=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve()
    require(root.is_dir(),'source root does not exist')
    patch(root)
    deterministic_zip(root,out)
    print(f'R2_ZIP_SHA256={sha(out)}')
    print(f'PAYLOAD_SHA256={sha(root/"academic_payload/index.html")}')
