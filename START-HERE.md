# Start here — no commands needed

## Windows app

1. Open [the Windows download page](https://github.com/thisisraihanm/service-path-check/releases/latest).
2. Under **Assets**, download **ServicePathCheck-Windows.zip**.
3. Right-click the ZIP and choose **Extract All**. Open the extracted folder.
4. Double-click **ServicePathCheck.exe**. Python is included inside the app.
5. Click **Try a safe example** first. It uses fictional data and does not check your own network or files.

## Use your own data

Type or paste a website address, then click **Check connection**. For an office file server, select **Windows file server** and enter the name provided by IT.

The **Read the result** screen says what happened and what you can do next. **Open detailed report** gives a browser report. **Save report copy** lets you keep or share an HTML report with IT. A report can contain private server or file names.

## If something is unclear

- **A little help is needed:** the screen explains what to select or what to ask IT to review.
- **Some checks could not finish:** treat the result as incomplete. Do not assume everything is fine.
- **The tool is checking:** leave it open. Large folders and unreachable servers can take time.
- **Windows blocks opening the app or saving settings:** ask IT to review or approve the tool. The apps are not code-signed. Windows settings collection respects the current PowerShell script policy.

## Source-code download

The GitHub **Code → Download ZIP** button downloads source code, which needs Python 3.11 or newer including Tcl/Tk. Extract it and double-click **Start-Windows.cmd**. For the version that includes Python, use the **Windows app** steps above.

Linux/macOS users with Python and Tk installed can run `python3 desktop.py`. The Windows settings collector is available only on Windows; comparing saved settings and the safe example work on other supported desktops.

The tool reads and reports. It does not repair configurations, copy backup files, or delete files. Successful connection checks do not prove the whole application works; matching backup contents do not replace a restore test.
