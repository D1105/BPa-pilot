import { useState } from 'react'
import Landing from './components/Landing'
import ChatWidget from './components/ChatWidget'
import AdminPanel from './components/AdminPanel'

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isAdminOpen, setIsAdminOpen] = useState(false)

  // Ctrl+Shift+A открывает админку
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'A') {
      setIsAdminOpen(true)
    }
  }

  return (
    <div className="min-h-screen" onKeyDown={handleKeyDown} tabIndex={0}>
      <Landing 
        onOpenChat={() => setIsChatOpen(true)} 
        onOpenAdmin={() => setIsAdminOpen(true)}
      />
      <ChatWidget isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
      <AdminPanel isOpen={isAdminOpen} onClose={() => setIsAdminOpen(false)} />
    </div>
  )
}

export default App
