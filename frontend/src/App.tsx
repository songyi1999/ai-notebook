import NoteEditor from './components/NoteEditor';
function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>AI笔记本</h1>
        <p>纯本地、AI增强的个人知识管理系统</p>
      </header>
      <main>
        <NoteEditor />
      </main>
    </div>
  )
}

export default App