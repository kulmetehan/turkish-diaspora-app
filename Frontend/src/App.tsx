import { useEffect, useState } from 'react';
import { API_BASE_URL, getHealth } from './lib/api';

export default function App() {
  const [health, setHealth] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const data = await getHealth();
      setHealth(data?.status ?? null);
    })();
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: 'system-ui, Arial, sans-serif' }}>
      <h1>Turkish Diaspora App</h1>
      <p>Hello World 👋</p>

      <hr style={{ margin: '16px 0' }} />

      <h2>Config</h2>
      <p>
        <strong>API base URL:</strong> {API_BASE_URL || '(not set)'}
      </p>

      <h2>Backend health</h2>
      <p>
        {health === null
          ? 'Proberen te verbinden… (of backend niet bereikbaar)'
          : `Backend zegt: ${health}`}
      </p>
    </div>
  );
}
