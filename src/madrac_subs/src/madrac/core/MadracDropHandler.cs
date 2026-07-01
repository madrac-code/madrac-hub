// Si modificas este archivo, recompila antes de commit:
//   csc /target:library /platform:AnyCPU /out:MadracDropHandler.dll MadracDropHandler.cs

using System;
using System.IO;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;
using Microsoft.Win32;

[ComImport]
[Guid("00000122-0000-0000-C000-000000000046")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IDropTarget
{
    void DragEnter([MarshalAs(UnmanagedType.Interface)] IDataObject pDataObj,
                   int grfKeyState, long pt, ref int pdwEffect);
    void DragOver(int grfKeyState, long pt, ref int pdwEffect);
    void DragLeave();
    void Drop([MarshalAs(UnmanagedType.Interface)] IDataObject pDataObj,
              int grfKeyState, long pt, ref int pdwEffect);
}

[ComImport]
[Guid("0000010B-0000-0000-C000-000000000046")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPersistFile
{
    void GetClassID(out Guid pClassID);
    int IsDirty();
    void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, int dwMode);
    void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, bool fRemember);
    void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
    [return: MarshalAs(UnmanagedType.LPWStr)] string GetCurFile();
}

[ComVisible(true)]
[Guid("B1C9A5E0-8F4D-4E7A-9C3D-2A1B6F8E0D4C")]
[ProgId("MadracSubs.DropHandler")]
public class MadracDropHandler : IPersistFile, IDropTarget
{
    private string _targetFile;

    public void GetClassID(out Guid pClassID)
    {
        pClassID = new Guid("B1C9A5E0-8F4D-4E7A-9C3D-2A1B6F8E0D4C");
    }

    public int IsDirty()
    {
        return 0;
    }

    public void Load(string pszFileName, int dwMode)
    {
        _targetFile = pszFileName;
        Log(string.Format("Load: {0}", _targetFile));
    }

    public void Save(string pszFileName, bool fRemember) { }
    public void SaveCompleted(string pszFileName) { }

    public string GetCurFile()
    {
        return _targetFile ?? "";
    }

    public void DragEnter(IDataObject pDataObj, int grfKeyState, long pt, ref int pdwEffect)
    {
        pdwEffect = 1;
    }

    public void DragOver(int grfKeyState, long pt, ref int pdwEffect)
    {
        pdwEffect = 1;
    }

    public void DragLeave() { }

    public void Drop(IDataObject pDataObj, int grfKeyState, long pt, ref int pdwEffect)
    {
        pdwEffect = 1;
        try
        {
            DropHandler(pDataObj);
        }
        catch (Exception ex)
        {
            Log(string.Format("Drop error: {0}", ex.Message));
        }
    }

    private void DropHandler(IDataObject dataObj)
    {
        if (string.IsNullOrEmpty(_targetFile))
        {
            Log("No target file (IPersistFile.Load not called)");
            return;
        }

        var srtFiles = new System.Collections.Generic.List<string>();

        FORMATETC fmt = new FORMATETC();
        fmt.cfFormat = 15;
        fmt.dwAspect = (DVASPECT)1;
        fmt.lindex = -1;
        fmt.tymed = (TYMED)1;

        STGMEDIUM med;
        dataObj.GetData(ref fmt, out med);

        try
        {
            IntPtr hDrop = med.unionmember;
            if (hDrop == IntPtr.Zero) return;

            int count = DragQueryFile(hDrop, -1, null, 0);
            Log(string.Format("Dropped {0} files", count));

            for (int i = 0; i < count; i++)
            {
                int len = DragQueryFile(hDrop, i, null, 0);
                if (len <= 0) continue;

                StringBuilder sb = new StringBuilder(len + 1);
                DragQueryFile(hDrop, i, sb, sb.Capacity);

                string file = sb.ToString();
                string ext = Path.GetExtension(file).ToLowerInvariant();
                if (ext == ".srt" || ext == ".ass" || ext == ".vtt")
                    srtFiles.Add(file);
            }
        }
        finally
        {
            ReleaseStgMedium(ref med);
        }

        if (srtFiles.Count == 0)
        {
            Log("No subtitle files in drop");
            return;
        }

        LaunchMux(_targetFile, srtFiles[0]);
    }

    private void LaunchMux(string video, string srt)
    {
        try
        {
            string exe = Registry.GetValue(
                @"HKEY_CURRENT_USER\Software\MadracSubs", "AppExe", "") as string;
            string script = Registry.GetValue(
                @"HKEY_CURRENT_USER\Software\MadracSubs", "ScriptPath", "") as string;
            string workDir = Registry.GetValue(
                @"HKEY_CURRENT_USER\Software\MadracSubs", "WorkDir", "") as string;

            if (string.IsNullOrEmpty(exe))
            {
                Log("Registry: AppExe not set");
                return;
            }

            string args;
            if (!string.IsNullOrEmpty(script))
                args = string.Format("\"{0}\" --fast-mux \"{1}\" \"{2}\"", script, video, srt);
            else
                args = string.Format("--fast-mux \"{0}\" \"{1}\"", video, srt);

            Log(string.Format("Launch: {0} {1}", exe, args));

            Process proc = new Process();
            proc.StartInfo.FileName = exe;
            proc.StartInfo.Arguments = args;
            proc.StartInfo.WorkingDirectory = string.IsNullOrEmpty(workDir)
                ? Path.GetDirectoryName(exe) : workDir;
            proc.StartInfo.UseShellExecute = false;
            proc.StartInfo.CreateNoWindow = true;
            proc.Start();
        }
        catch (Exception ex)
        {
            Log(string.Format("Launch error: {0}", ex.Message));
        }
    }

    private static void Log(string msg)
    {
        try
        {
            string logPath = Path.Combine(Path.GetTempPath(), "MadracDropHandler.log");
            using (StreamWriter w = File.AppendText(logPath))
            {
                w.WriteLine(string.Format("{0:HH:mm:ss} [{1}] {2}",
                    DateTime.Now, System.Threading.Thread.CurrentThread.ManagedThreadId, msg));
            }
        }
        catch { }
    }

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern int DragQueryFile(IntPtr hDrop, int iFile,
        StringBuilder lpszFile, int cchFiles);

    [DllImport("ole32.dll")]
    private static extern int ReleaseStgMedium(ref STGMEDIUM medium);
}
