export default function AdminDashboardTest() {
  return (
    <div style={{ padding: '20px', backgroundColor: '#f0f0f0', minHeight: '100vh' }}>
      <h1>Admin Dashboard Test Component</h1>
      <p>If you see this, the admin routing is working!</p>
      <p>Current URL: {window.location.pathname}</p>
      <p>Time: {new Date().toLocaleTimeString()}</p>
    </div>
  );
}