"""
GNN Swarm Behavior Model (Phase 663)

이 모듈은 다중 에이전트 환경에서 각 드론을 노드(Node)로, 
인접 통신/물리적 근접성을 간선(Edge)으로 정의하여
그래프 신경망(GNN) 기반의 충돌 회피 벡터 및 편대 유지 벡터를 
계산하는 프레임워크를 제공합니다.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F

class GraphAttentionLayer(nn.Module):
    def __init__(self, in_features, out_features, alpha=0.2):
        """
        드론 간의 관계 중요도를 계산하기 위한 단순화된 Graph Attention Layer (GAT).
        """
        super(GraphAttentionLayer, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        
        self.W = nn.Linear(in_features, out_features, bias=False)
        self.a = nn.Linear(2 * out_features, 1, bias=False)
        self.leakyrelu = nn.LeakyReLU(alpha)

    def forward(self, h, adj):
        """
        Args:
            h: [N, in_features] 각 드론의 특성 벡터 (위치, 속도 등)
            adj: [N, N] 인접 행렬 (상호작용 가능 여부)
        """
        Wh = self.W(h) # [N, out_features]
        N = Wh.size(0)

        # [N, N, 2 * out] 생성
        a_input = torch.cat([Wh.repeat(1, N).view(N * N, -1), Wh.repeat(N, 1)], dim=1).view(N, -1, 2 * self.out_features)
        
        # 어텐션 스코어 계산 [N, N]
        e = self.leakyrelu(self.a(a_input).squeeze(2))

        # 인접하지 않은(adj==0) 에지는 매우 작은 값으로 마스킹
        zero_vec = -9e15 * torch.ones_like(e)
        attention = torch.where(adj > 0, e, zero_vec)
        attention = F.softmax(attention, dim=1)

        # 가중 합 계산
        h_prime = torch.matmul(attention, Wh)
        return F.elu(h_prime)

class GNNSwarmModel(nn.Module):
    def __init__(self, node_features=6, hidden_dim=32, output_features=3):
        """
        드론 군집의 상태를 입력받아 회피/편대 제어 명령 벡터를 산출하는 GNN.
        
        Args:
            node_features: 상태 벡터 크기 (기본: x,y,z, vx,vy,vz = 6)
            hidden_dim: GNN 은닉층 크기
            output_features: 출력 행동 벡터 (ax, ay, az = 3)
        """
        super(GNNSwarmModel, self).__init__()
        self.layer1 = GraphAttentionLayer(node_features, hidden_dim)
        self.layer2 = GraphAttentionLayer(hidden_dim, hidden_dim)
        self.fc = nn.Linear(hidden_dim, output_features)

    def forward(self, x, adj):
        """
        추론 함수
        Args:
            x: [N, 6] 위치 및 속도 데이터
            adj: [N, N] 드론 간 통신망/레이더 인접 행렬
        Returns:
            [N, 3] 각 드론의 추천 가속도 벡터
        """
        # Graph Attention 인코딩
        h1 = self.layer1(x, adj)
        h2 = self.layer2(h1, adj)
        
        # 행동 벡터 매핑
        actions = self.fc(h2)
        
        # 최대 가속도 클리핑 (Tanh 후 스케일 조정)
        return torch.tanh(actions) * 10.0

def build_adjacency_matrix(positions, communication_range=500.0):
    """
    관측된 드론 위치 그룹으로부터 간단한 인접 행렬(Adjacency Matrix)을 구성합니다.
    """
    import numpy as np
    pos_arr = np.array(positions)
    N = len(pos_arr)
    adj = np.zeros((N, N), dtype=np.float32)
    
    for i in range(N):
        for j in range(N):
            dist = np.linalg.norm(pos_arr[i] - pos_arr[j])
            if dist <= communication_range:
                adj[i, j] = 1.0
                
    return torch.tensor(adj)
