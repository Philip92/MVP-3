import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export function AuthCallback() {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const { processSession } = useAuth();

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const handleCallback = async () => {
      const hash = window.location.hash;
      console.log('AuthCallback: Processing hash:', hash);
      const params = new URLSearchParams(hash.substring(1));
      const sessionId = params.get('session_id');
      console.log('AuthCallback: Session ID found:', sessionId ? 'yes' : 'no');

      if (sessionId) {
        try {
          console.log('AuthCallback: Calling processSession...');
          const userData = await processSession(sessionId);
          console.log('AuthCallback: Session processed successfully', userData?.email);
          // Clear the hash and navigate with user data
          window.history.replaceState(null, '', '/dashboard');
          navigate('/dashboard', { replace: true, state: { user: userData } });
        } catch (error) {
          console.error('AuthCallback: Session processing failed:', error?.response?.data || error.message);
          navigate('/', { replace: true });
        }
      } else {
        console.log('AuthCallback: No session_id in hash, redirecting to home');
        navigate('/', { replace: true });
      }
    };

    handleCallback();
  }, [navigate, processSession]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
        <p className="mt-4 text-muted-foreground">Signing you in...</p>
      </div>
    </div>
  );
}
