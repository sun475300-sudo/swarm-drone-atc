"""
Diffusion Planner (Phase 664)

이 모듈은 Denoising Diffusion Probabilistic Models (DDPM) 
개념을 도입하여, 무작위 노이즈에서 출발하여 복잡한 도심 장애물을 
회피하는 안전 경로를 생성하는 경로 계획 프레임워크입니다.
"""
import torch
import torch.nn as nn

class PathDiffusionUNet(nn.Module):
    def __init__(self, in_channels=1, hidden_dim=64):
        """
        1D Conv 기반 U-Net 구조. (이미지 대신 1D 경로 시퀀스를 제어함)
        입력: [Batch, 1, Seq_len, 3(xyz)] 텐서
        """
        super(PathDiffusionUNet, self).__init__()
        
        # 실제 환경에서는 훨씬 깊은 U-Net이 필요하지만 시뮬레이션 목적의 간소화 모델
        self.enc1 = nn.Conv1d(3, hidden_dim, kernel_size=3, padding=1)
        self.enc2 = nn.Conv1d(hidden_dim, hidden_dim*2, kernel_size=3, padding=1)
        
        self.dec1 = nn.Conv1d(hidden_dim*2, hidden_dim, kernel_size=3, padding=1)
        self.dec2 = nn.Conv1d(hidden_dim, 3, kernel_size=3, padding=1)
        
        self.act = nn.SiLU()

    def forward(self, x, t):
        """
        Args:
            x: 노이즈가 낀 경로 [B, 3, Seq_len]
            t: 확산 타임스텝 임베딩 [B, dim]
        """
        # (타임스텝 t 인젝션은 생략된 단순 모델)
        h1 = self.act(self.enc1(x))
        h2 = self.act(self.enc2(h1))
        
        h3 = self.act(self.dec1(h2))
        h4 = self.dec2(h3)
        return h4

class DDPMScheduler:
    def __init__(self, num_timesteps=100, beta_start=1e-4, beta_end=0.02):
        self.num_timesteps = num_timesteps
        self.betas = torch.linspace(beta_start, beta_end, num_timesteps)
        self.alphas = 1.0 - self.betas
        self.alphas_cumprod = torch.cumprod(self.alphas, axis=0)
        
    def add_noise(self, original_path, t):
        """
        경로 데이터에 정방향 확산 노이즈를 주입합니다.
        """
        noise = torch.randn_like(original_path)
        sqrt_alpha_cumprod = torch.sqrt(self.alphas_cumprod[t])
        sqrt_one_minus_alpha_cumprod = torch.sqrt(1 - self.alphas_cumprod[t])
        
        # [B, 3, seq_len] 형태의 브로드캐스트 처리가 필요
        noisy_path = sqrt_alpha_cumprod.view(-1, 1, 1) * original_path \
                   + sqrt_one_minus_alpha_cumprod.view(-1, 1, 1) * noise
        return noisy_path, noise

def generate_path_inference(model: PathDiffusionUNet, scheduler: DDPMScheduler, seq_len=50, device="cpu") -> torch.Tensor:
    """
    DDPM 역전파 생성 프로세스. 랜덤 노이즈 궤적에서 최적 궤적으로 복원.
    """
    model.eval()
    with torch.no_grad():
        x = torch.randn(1, 3, seq_len).to(device)
        for i in reversed(range(scheduler.num_timesteps)):
            t = torch.tensor([i], dtype=torch.long, device=device)
            # 노이즈 예측
            predicted_noise = model(x, t)
            
            alpha = scheduler.alphas[t]
            alpha_cumprod = scheduler.alphas_cumprod[t]
            beta = scheduler.betas[t]
            
            if i > 0:
                noise = torch.randn_like(x)
            else:
                noise = torch.zeros_like(x)
                
            x = 1 / torch.sqrt(alpha) * (x - ((1 - alpha) / torch.sqrt(1 - alpha_cumprod)) * predicted_noise) \
                + torch.sqrt(beta) * noise
                
    return x
