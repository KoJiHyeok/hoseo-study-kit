// 할일.app — 크롬과 분리된 네이티브 창(WKWebView). 화면·데이터는 전부 dash/app.py 가 담당하고,
// 이 껍데기는 서버를 띄우고(`app.py --no-open`) 창에 붙이기만 한다. 빌드: dash/make-mac-app.sh
import Cocoa
import WebKit

let pageURL = URL(string: "http://127.0.0.1:8765/")!
let paper = NSColor(red: 0xfd / 255, green: 0xfb / 255, blue: 0xf3 / 255, alpha: 1)

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var web: WKWebView!
    var server: Process?
    var retries = 0

    func applicationDidFinishLaunching(_ n: Notification) {
        startServer()
        buildMenu()
        web = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
        web.navigationDelegate = self
        web.setValue(false, forKey: "drawsBackground")      // 로딩 중 흰 화면 번쩍임 방지
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 800),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "할일"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true           // 제목줄도 종이색
        window.backgroundColor = paper
        window.minSize = NSSize(width: 380, height: 500)
        window.contentView = web
        window.center()
        window.setFrameAutosaveName("HoseoDash")            // 위치·크기 기억
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        load()
    }

    func load() { web.load(URLRequest(url: pageURL)) }

    // 서버가 뜰 때까지 재시도 (최대 ~10초)
    func webView(_ w: WKWebView, didFailProvisionalNavigation nav: WKNavigation!, withError e: Error) {
        guard retries < 50 else { return }
        retries += 1
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self.load() }
    }

    func startServer() {
        let info = Bundle.main.infoDictionary ?? [:]
        guard let py = info["HoseoPython"] as? String, let dash = info["HoseoDash"] as? String else { return }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: py)
        p.arguments = [dash + "/app.py", "--no-open"]       // 이미 떠 있으면 스스로 바로 종료
        p.currentDirectoryURL = URL(fileURLWithPath: dash).deletingLastPathComponent()
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
        p.environment = env
        try? p.run()
        server = p
    }

    // 종료: 쓰던 메모 저장 → 서버에 SIGTERM (서버가 메모를 commit+push 하고 끝난다)
    func applicationShouldTerminate(_ app: NSApplication) -> NSApplication.TerminateReply {
        web.evaluateJavaScript("typeof saveMemo === 'function' && saveMemo()") { _, _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                if let p = self.server, p.isRunning { p.terminate() }
                app.reply(toApplicationShouldTerminate: true)
            }
        }
        return .terminateLater
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { true }

    @objc func reload(_ s: Any?) { web.reload() }

    func buildMenu() {
        let main = NSMenu()
        func sub(_ title: String, _ items: [NSMenuItem]) {
            let top = NSMenuItem(); let m = NSMenu(title: title)
            items.forEach { m.addItem($0) }
            top.submenu = m; main.addItem(top)
        }
        func item(_ t: String, _ a: Selector?, _ k: String, _ mods: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let i = NSMenuItem(title: t, action: a, keyEquivalent: k); i.keyEquivalentModifierMask = mods; return i
        }
        sub("할일", [item("할일 종료", #selector(NSApplication.terminate(_:)), "q")])
        sub("편집", [item("실행 취소", Selector(("undo:")), "z"),
                     item("실행 복귀", Selector(("redo:")), "z", [.command, .shift]),
                     .separator(),
                     item("오려두기", #selector(NSText.cut(_:)), "x"),
                     item("복사하기", #selector(NSText.copy(_:)), "c"),
                     item("붙여넣기", #selector(NSText.paste(_:)), "v"),
                     item("전체 선택", #selector(NSText.selectAll(_:)), "a")])
        sub("보기", [item("새로고침", #selector(reload(_:)), "r")])
        sub("윈도우", [item("닫기", #selector(NSWindow.performClose(_:)), "w"),
                      item("최소화", #selector(NSWindow.miniaturize(_:)), "m")])
        NSApp.mainMenu = main
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
