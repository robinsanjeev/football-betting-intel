import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ActiveSignals from './pages/ActiveSignals'
import PerformanceAccuracy from './pages/PerformanceAccuracy'
import TradeLog from './pages/TradeLog'
import Documentation from './pages/Documentation'
import ModelInsights from './pages/ModelInsights'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ActiveSignals />} />
          <Route path="/performance" element={<PerformanceAccuracy />} />
          <Route path="/trades" element={<TradeLog />} />
          <Route path="/insights" element={<ModelInsights />} />
          <Route path="/docs" element={<Documentation />} />
          <Route path="/accuracy" element={<Navigate to="/performance" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
