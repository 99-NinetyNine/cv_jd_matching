import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import CandidateDashboard from './pages/CandidateDashboard';
import AdminDashboard from './pages/AdminDashboard';
import Login from './pages/Login';
import Signup from './pages/Signup';
import HirerDashboard from './pages/HirerDashboard';
import PostJob from './pages/PostJob';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/dashboard" element={<CandidateDashboard />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/hirer" element={<HirerDashboard />} />
        <Route path="/hirer/post-job" element={<PostJob />} />
        <Route path="/" element={<Navigate to="/login" replace />} />

      </Routes>
    </Router>
  );
}

export default App;
