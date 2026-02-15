import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Code2, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      await login(email, password);
      toast.success('Welcome back!');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-md bg-white/10 flex items-center justify-center">
            <Code2 className="w-5 h-5 text-white" strokeWidth={2} />
          </div>
          <span className="text-xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            JSHost
          </span>
        </div>
        <div>
          <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-tight mb-6" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Secure JavaScript<br />delivery, simplified.
          </h1>
          <p className="text-lg text-slate-400 leading-relaxed max-w-md">
            Host, manage, and deliver JavaScript snippets to whitelisted domains with complete control.
          </p>
        </div>
        <p className="text-sm text-slate-500">Project-Based JavaScript Hosting Platform</p>
      </div>

      {/* Right panel - Login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-9 h-9 rounded-md bg-[#0F172A] flex items-center justify-center">
              <Code2 className="w-4 h-4 text-white" strokeWidth={2} />
            </div>
            <span className="text-lg font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>JSHost</span>
          </div>

          <Card className="border-0 shadow-none">
            <CardHeader className="px-0 pt-0">
              <CardTitle className="text-2xl font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
                Sign in
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Enter your credentials to access your account
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="email" className="label-caps">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    data-testid="login-email-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password" className="label-caps">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    data-testid="login-password-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-[#0F172A] hover:bg-[#1E293B] text-white rounded-md py-2.5 font-medium active:scale-95 transition-transform"
                  disabled={loading}
                  data-testid="login-submit-btn"
                >
                  {loading ? 'Signing in...' : 'Sign in'}
                  {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
                </Button>
              </form>
              <p className="mt-6 text-sm text-center text-muted-foreground">
                Contact your administrator for account access
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
