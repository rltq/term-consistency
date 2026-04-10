# URL: 지금 열려있는 최신 번역 PR 선택 (04/10 기준)
# https://github.com/PyTorchKorea/tutorials-kr/pull/1059

## poc.terms.kr 데이터 구조

```json
{
  "term": "attention",
  "meanings": [
    {
      "korean": "어텐션",
      "definition": "입력 시퀀스의 각 요소에 서로 다른 가중치를 부여하여 중요한 정보에 집중하는 메커니즘",
      "examples": [
        {
          "en": "The Transformer model uses a self-attention mechanism.",
          "ko": "트랜스포머 모델은 셀프 어텐션 메커니즘을 사용한다."
        }
      ],
      "synonyms": ["주의 메커니즘", "집중 메커니즘"]
    }
  ]
}
```

# 원본 diff

+64
-75
Lines changed: 64 additions & 75 deletions
Original file line number	Diff line number	Diff line change
# -*- coding: utf-8 -*-
"""
Per-sample-gradients
샘플별 변화도(Per-sample-gradients)
====================
**번역:** `최도윤 <https://github.com/0000000000>`_
What is it?
-----------
Per-sample-gradient computation is computing the gradient for each and every
sample in a batch of data. It is a useful quantity in differential privacy,
meta-learning, and optimization research.
샘플별 변화도 계산은 데이터 한 배치의 모든 샘플에 대해
변화도를 계산하는 것입니다. 차분 프라이버시(differential privacy), 메타 학습, 최적화 연구에서
유용하게 사용됩니다.
.. note::
   This tutorial requires PyTorch 2.0.0 or later.
   이 튜토리얼은 Pytorch 2.0.0 이상의 버전을 필요로 합니다.
"""

import torch.nn.functional as F
torch.manual_seed(0)

# Here's a simple CNN and loss function:
# 다음은 간단한 CNN 모델과 손실 함수입니다.

class SimpleCNN(nn.Module):
    def __init__(self):


######################################################################
# Let’s generate a batch of dummy data and pretend that we’re working with an MNIST dataset.
# The dummy images are 28 by 28 and we use a minibatch of size 64.
# MNIST 데이터셋을 사용한다고 가정하고, 더미(dummy) 데이터 배치를 만들었습니다.
# 각 데이터는 28x28의 크기를 가지고, 미니배치의 크기를 64로 뒀습니다. 

device = 'cuda'

targets = torch.randint(10, (64,), device=device)

######################################################################
# In regular model training, one would forward the minibatch through the model,
# and then call .backward() to compute gradients.  This would generate an
# 'average' gradient of the entire mini-batch:
# 미니배치를 모델에 주고, .backward()를 호출해서
# 변화도를 계산하는 것이 일반적인 모델 학습 방법입니다. 
# 곧, 그 미니배치 전체의 '평균적인' 변화도를 생성할 수 있습니다:

model = SimpleCNN().to(device=device)
predictions = model(data)  # move the entire mini-batch through the model
predictions = model(data)  # 전체 미니배치를 모델에 통과시킵니다.

loss = loss_fn(predictions, targets)
loss.backward()  # back propagate the 'average' gradient of this mini-batch
loss.backward()  # 미니배치의 평균 변화도를 역전파시킵니다.

######################################################################
# In contrast to the above approach, per-sample-gradient computation is
# equivalent to:
# 위 방법과는 반대로, 샘플별 변화도 계산은 다음과 같습니다:
#
# - for each individual sample of the data, perform a forward and a backward
#   pass to get an individual (per-sample) gradient.
# - 데이터의 각 샘플에 대해, 순전파와 역전파를 수행하여
#   개별적인(샘플별) 변화도를 구합니다.

def compute_grad(sample, target):
    sample = sample.unsqueeze(0)  # prepend batch dimension for processing
    sample = sample.unsqueeze(0)  # 처리를 위해선 배치 차원을 추가해야 합니다.
    target = target.unsqueeze(0)

    prediction = model(sample)


def compute_sample_grads(data, targets):
    """ manually process each sample with per sample gradient """
    """ 각 샘플에 대한 변화도를 직접 계산합니다 """
    sample_grads = [compute_grad(data[i], targets[i]) for i in range(batch_size)]
    sample_grads = zip(*sample_grads)
    sample_grads = [torch.stack(shards) for shards in sample_grads]
per_sample_grads = compute_sample_grads(data, targets)

######################################################################
# ``sample_grads[0]`` is the per-sample-grad for model.conv1.weight.
# ``model.conv1.weight.shape`` is ``[32, 1, 3, 3]``; notice how there is one
# gradient, per sample, in the batch for a total of 64.
# ``sample_grads[0]`` 는 ``model.conv1.weight``에 대한 샘플별 변화도입니다.
# ``model.conv1.weight.shape``는 ``[32, 1, 3, 3]``입니다. 배치 내부에 샘플당 하나씩,
# 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다.

print(per_sample_grads[0].shape)

######################################################################
# Per-sample-grads, *the efficient way*, using function transforms
# 함수 변환(Function Transforms)을 이용한 *효율적인* 샘플별 변화도 계산
# ----------------------------------------------------------------
# We can compute per-sample-gradients efficiently by using function transforms.
# 함수 변환을 사용하면 더 효율적으로 샘플별 변화도를 알 수 있습니다.
#
# The ``torch.func`` function transform API transforms over functions.
# Our strategy is to define a function that computes the loss and then apply
# transforms to construct a function that computes per-sample-gradients.
# ``torch.func``의 함수 변환 API는 함수를 대상으로 동작합니다.
# 먼저 손실 함수를 정의하고, 변환해서 
# 샘플별 변화도를 계산하는 함수를 형성하는 것이 전략입니다.
#
# We'll use the ``torch.func.functional_call`` function to treat an ``nn.Module``
# like a function.
# ``torch.func.functional_call`` 함수를 가지고 ``nn.Module``을 함수처럼 다룰 것입니다.
#
# First, let’s extract the state from ``model`` into two dictionaries,
# parameters and buffers. We'll be detaching them because we won't use
# regular PyTorch autograd (e.g. Tensor.backward(), torch.autograd.grad).
# 우선, ``model``의 상태를 매개변수와 버퍼, 두 딕셔너리로 추출해야 합니다.
# 일반적인 PyTorch autograd(예: Tensor.backward(), torch.autograd.grad)를
# 사용하지 않을 것이기 때문입니다.

from torch.func import functional_call, vmap, grad

params = {k: v.detach() for k, v in model.named_parameters()}
buffers = {k: v.detach() for k, v in model.named_buffers()}

######################################################################
# Next, let's define a function to compute the loss of the model given a
# single input rather than a batch of inputs. It is important that this
# function accepts the parameters, the input, and the target, because we will
# be transforming over them.
# 다음으로, 배치가 아닌 단일 입력에 대한 모델의 손실을 계산하는 함수를 정의합시다.
# 이때 매개변수, 입력, 그리고 목표 변수(target)을 함수가 인자로 받게 하는 것이 중요합니다.
# 그 인자들에 대해 변환을 적용할 것이기 때문입니다.
#
# Note - because the model was originally written to handle batches, we’ll
# use ``torch.unsqueeze`` to add a batch dimension.
# 참고 - 모델은 배치를 원래 처리하도록 작성되었으니, 
# ``torch.unsqueeze``로 배치 차원을 추가해 줍니다.

def compute_loss(params, buffers, sample, target):
    batch = sample.unsqueeze(0)
    return loss

######################################################################
# Now, let’s use the ``grad`` transform to create a new function that computes
# the gradient with respect to the first argument of ``compute_loss``
# (i.e. the ``params``).
# 이제, ``grad`` 변환을 사용해서 ``compute_loss``의 첫번째 인자인 
# 매개변수 ``params``에 대해 변화도를 측정하는 새로운 함수를 만들어 봅시다.

ft_compute_grad = grad(compute_loss)

######################################################################
# The ``ft_compute_grad`` function computes the gradient for a single
# (sample, target) pair. We can use ``vmap`` to get it to compute the gradient
# over an entire batch of samples and targets. Note that
# ``in_dims=(None, None, 0, 0)`` because we wish to map ``ft_compute_grad`` over
# the 0th dimension of the data and targets, and use the same ``params`` and
# buffers for each.
# ``ft_compute_grad``는 단일 (샘플, 목표 변수) 쌍에 대한 변화도를 계산하는 함수입니다.
# ``vmap``을 사용하면 전체 샘플 및 목표 변수들 배치에 대한 변화도를 알 수 있습니다.
# 이때 ``in_dims=(None, None, 0, 0)``로 설정했는데, 이는 데이터와 목표 변수의 
# 0번째 차원에 대해 ``ft_compute_grad``를 매핑하고, 매개변수와 버퍼는
# 각 샘플에 대해 똑같이 사용하기 위함입니다.

ft_compute_sample_grad = vmap(ft_compute_grad, in_dims=(None, None, 0, 0))

######################################################################
# Finally, let's used our transformed function to compute per-sample-gradients:
# 마지막으로, 변환됨 함수를 이용해 샘플별 변화도를 계산합니다.

ft_per_sample_grads = ft_compute_sample_grad(params, buffers, data, targets)

######################################################################
# we can double check that the results using ``grad`` and ``vmap`` match the
# results of hand processing each one individually:
# ``grad``와 ``vmap``을 사용한 결과가 수동으로 하나씩 처리한 결과와 일치하는지 확인합니다:

for per_sample_grad, ft_per_sample_grad in zip(per_sample_grads, ft_per_sample_grads.values()):
    assert torch.allclose(per_sample_grad, ft_per_sample_grad, atol=1.2e-1, rtol=1e-5)

######################################################################
# A quick note: there are limitations around what types of functions can be
# transformed by ``vmap``. The best functions to transform are ones that are pure
# functions: a function where the outputs are only determined by the inputs,
# and that have no side effects (e.g. mutation). ``vmap`` is unable to handle
# mutation of arbitrary Python data structures, but it is able to handle many
# in-place PyTorch operations.
# 참고: ``vmap``으로 변환할 수 있는 함수의 유형에는 몇 가지 제한이 있습니다. 
# 가장 변환하기 좋은 함수는 순수 함수(pure function)입니다. 즉, 출력이 오직 입력에 
# 의해서만 결정되고 값 수정과 같은 부작용이 없는 함수입니다. 
# ``vmap``은 임의의 파이썬 데이터 구조를 수정하는 작업은 처리할 수 없지만, 
# 많은 PyTorch 인플레이스(in-place) 연산은 처리할 수 있습니다.
#
# Performance comparison
# 성능 비교
# ----------------------
#
# Curious about how the performance of ``vmap`` compares?
# ``vmap``의 성능이 얼마나 차이 나는지 궁금하신가요?
#
# Currently the best results are obtained on newer GPU's such as the A100
# (Ampere) where we've seen up to 25x speedups on this example, but here are
# some results on our build machines:
# 현재 A100(Ampere)과 같은 최신 GPU에서 가장 좋은 결과를 얻을 수 있고,
# 이 예제에서 최대 25배의 속도 향상을 확인했습니다. 한편 다음은 빌드 장비에서의 결과입니다:

def get_perf(first, first_descriptor, second, second_descriptor):
    """takes torch.benchmark objects and compares delta of second vs first."""
    """torch.benchmark 객체들을 받아서 첫번째와 두번째의 차이를 비교합니다"""
    second_res = second.times[0]
    first_res = first.times[0]

get_perf(with_vmap_timing, "vmap", no_vmap_timing, "no vmap")

######################################################################
# There are other optimized solutions (like in https://github.com/pytorch/opacus)
# to computing per-sample-gradients in PyTorch that also perform better than
# the naive method. But it’s cool that composing ``vmap`` and ``grad`` give us a
# nice speedup.
# PyTorch에는 이런 방법보다 성능이 뛰어난 다른 최적화 솔루션
# (예: https://github.com/pytorch/opacus)들도 존재합니다. 
# 하지만 ``vmap``과 ``grad``를 조합하는 것만으로 이 정도의 속도 향상을
# 이룰 수 있다는 사실이 멋지지 않나요?
#
# In general, vectorization with ``vmap`` should be faster than running a function
# in a for-loop and competitive with manual batching. There are some exceptions
# though, like if we haven’t implemented the ``vmap`` rule for a particular
# operation or if the underlying kernels weren’t optimized for older hardware
# (GPUs). If you see any of these cases, please let us know by opening an issue
# at on GitHub.
# 일반적으로 ``vmap``을 이용한 벡터화는 함수를 반복문에서 실행하는 것보다 빠르고, 
# 수동 배칭(manual batching)과 경쟁할 만한 성능을 보여줍니다. 
# 다만 특정 연산에 대해 ``vmap`` 규칙이 없거나, 하위 커널이 오래된 하드웨어(GPU)에 
# 최적화되지 않은 경우 등에서 예외가 있을 수 있습니다. 이런 경우를 하나라도 발견한다면, 
# GitHub에 이슈를 남겨 알려주시기 바랍니다.

----------------------------------------------------------------------------------------------------------


# Matched


file -> intermediate_source/per_sample_grads.py
origin -> loss
expected -> ['손실', '로스']
matched
	# 다음은 간단한 CNN 모델과 손실 함수입니다.

file -> intermediate_source/per_sample_grads.py
origin -> dataset
expected -> ['데이터셋']
matched
	# MNIST 데이터셋을 사용한다고 가정하고, 더미(dummy) 데이터 배치를 만들었습니다. # 각 데이터는 28x28의 크기를 가지고, 미니배치의 크기를 64로 뒀습니다.

file -> intermediate_source/per_sample_grads.py
origin -> batch
expected -> ['배치']
matched
	# MNIST 데이터셋을 사용한다고 가정하고, 더미(dummy) 데이터 배치를 만들었습니다. # 각 데이터는 28x28의 크기를 가지고, 미니배치의 크기를 64로 뒀습니다.

file -> intermediate_source/per_sample_grads.py
origin -> mini-batch
expected -> ['미니배치']
matched
	# 미니배치를 모델에 주고, .backward()를 호출해서 # 변화도를 계산하는 것이 일반적인 모델 학습 방법입니다. # 곧, 그 미니배치 전체의 '평균적인' 변화도를 생성할 수 있습니다: # 위 방법과는 반대로, 샘플별 변화도 계산은 다음과 같습니다: # - 데이터의 각 샘플에 대해, 순전파와 역전파를 수행하여 #   개별적인(샘플별) 변화도를 구합니다.

file -> intermediate_source/per_sample_grads.py
origin -> batch
expected -> ['배치']
matched
	# 미니배치를 모델에 주고, .backward()를 호출해서 # 변화도를 계산하는 것이 일반적인 모델 학습 방법입니다. # 곧, 그 미니배치 전체의 '평균적인' 변화도를 생성할 수 있습니다: # 위 방법과는 반대로, 샘플별 변화도 계산은 다음과 같습니다: # - 데이터의 각 샘플에 대해, 순전파와 역전파를 수행하여 #   개별적인(샘플별) 변화도를 구합니다.

file -> intermediate_source/per_sample_grads.py
origin -> model
expected -> ['모델', '모형']
matched
	# 미니배치를 모델에 주고, .backward()를 호출해서 # 변화도를 계산하는 것이 일반적인 모델 학습 방법입니다. # 곧, 그 미니배치 전체의 '평균적인' 변화도를 생성할 수 있습니다: # 위 방법과는 반대로, 샘플별 변화도 계산은 다음과 같습니다: # - 데이터의 각 샘플에 대해, 순전파와 역전파를 수행하여 #   개별적인(샘플별) 변화도를 구합니다.

file -> intermediate_source/per_sample_grads.py
origin -> batch
expected -> ['배치']
matched
	#  는  에 대한 샘플별 변화도입니다. #  는  입니다. 배치 내부에 샘플당 하나씩, # 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다. # 함수 변환(Function Transforms)을 이용한 *효율적인* 샘플별 변화도 계산 # 함수 변환을 사용하면 더 효율적으로 샘플별 변화도를 알 수 있습니다. #  의 함수 변환 API는 함수를 대상으로 동작합니다. # 먼저 손실 함수를 정의하고, 변환해서 # 샘플별 변화도를 계산하는 함수를 형성하는 것이 전략입니다. #  함수를 가지고  을 함수처럼 다룰 것입니다. # 우선,  의 상태를 매개변수와 버퍼, 두 딕셔너리로 추출해야 합니다. # 일반적인 PyTorch autograd(예: Tensor.backward(), torch.autograd.grad)를 # 사용하지 않을 것이기 때문입니다.

file -> intermediate_source/per_sample_grads.py
origin -> loss
expected -> ['손실', '로스']
matched
	#  는  에 대한 샘플별 변화도입니다. #  는  입니다. 배치 내부에 샘플당 하나씩, # 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다. # 함수 변환(Function Transforms)을 이용한 *효율적인* 샘플별 변화도 계산 # 함수 변환을 사용하면 더 효율적으로 샘플별 변화도를 알 수 있습니다. #  의 함수 변환 API는 함수를 대상으로 동작합니다. # 먼저 손실 함수를 정의하고, 변환해서 # 샘플별 변화도를 계산하는 함수를 형성하는 것이 전략입니다. #  함수를 가지고  을 함수처럼 다룰 것입니다. # 우선,  의 상태를 매개변수와 버퍼, 두 딕셔너리로 추출해야 합니다. # 일반적인 PyTorch autograd(예: Tensor.backward(), torch.autograd.grad)를 # 사용하지 않을 것이기 때문입니다.

file -> intermediate_source/per_sample_grads.py
origin -> batch
expected -> ['배치']
matched
	# 다음으로, 배치가 아닌 단일 입력에 대한 모델의 손실을 계산하는 함수를 정의합시다. # 이때 매개변수, 입력, 그리고 목표 변수(target)을 함수가 인자로 받게 하는 것이 중요합니다. # 그 인자들에 대해 변환을 적용할 것이기 때문입니다. # 참고 - 모델은 배치를 원래 처리하도록 작성되었으니, #  로 배치 차원을 추가해 줍니다.

file -> intermediate_source/per_sample_grads.py
origin -> model
expected -> ['모델', '모형']
matched
	# 다음으로, 배치가 아닌 단일 입력에 대한 모델의 손실을 계산하는 함수를 정의합시다. # 이때 매개변수, 입력, 그리고 목표 변수(target)을 함수가 인자로 받게 하는 것이 중요합니다. # 그 인자들에 대해 변환을 적용할 것이기 때문입니다. # 참고 - 모델은 배치를 원래 처리하도록 작성되었으니, #  로 배치 차원을 추가해 줍니다.

file -> intermediate_source/per_sample_grads.py
origin -> loss
expected -> ['손실', '로스']
matched
	# 다음으로, 배치가 아닌 단일 입력에 대한 모델의 손실을 계산하는 함수를 정의합시다. # 이때 매개변수, 입력, 그리고 목표 변수(target)을 함수가 인자로 받게 하는 것이 중요합니다. # 그 인자들에 대해 변환을 적용할 것이기 때문입니다. # 참고 - 모델은 배치를 원래 처리하도록 작성되었으니, #  로 배치 차원을 추가해 줍니다.

file -> intermediate_source/per_sample_grads.py
origin -> in-place
expected -> ['제자리']
matched(brace)
	# 이제,  변환을 사용해서  의 첫번째 인자인 # 매개변수  에 대해 변화도를 측정하는 새로운 함수를 만들어 봅시다. #  는 단일 (샘플, 목표 변수) 쌍에 대한 변화도를 계산하는 함수입니다. #  을 사용하면 전체 샘플 및 목표 변수들 배치에 대한 변화도를 알 수 있습니다. # 이때  로 설정했는데, 이는 데이터와 목표 변수의 # 0번째 차원에 대해  를 매핑하고, 매개변수와 버퍼는 # 각 샘플에 대해 똑같이 사용하기 위함입니다. # 마지막으로, 변환됨 함수를 이용해 샘플별 변화도를 계산합니다. #  와  을 사용한 결과가 수동으로 하나씩 처리한 결과와 일치하는지 확인합니다: # 참고:  으로 변환할 수 있는 함수의 유형에는 몇 가지 제한이 있습니다. # 가장 변환하기 좋은 함수는 순수 함수(pure function)입니다. 즉, 출력이 오직 입력에 # 의해서만 결정되고 값 수정과 같은 부작용이 없는 함수입니다. #  은 임의의 파이썬 데이터 구조를 수정하는 작업은 처리할 수 없지만, # 많은 PyTorch 인플레이스(in-place) 연산은 처리할 수 있습니다. # 성능 비교 #  의 성능이 얼마나 차이 나는지 궁금하신가요? # 현재 A100(Ampere)과 같은 최신 GPU에서 가장 좋은 결과를 얻을 수 있고, # 이 예제에서 최대 25배의 속도 향상을 확인했습니다. 한편 다음은 빌드 장비에서의 결과입니다:

file -> intermediate_source/per_sample_grads.py
origin -> batch
expected -> ['배치']
matched
	# 이제,  변환을 사용해서  의 첫번째 인자인 # 매개변수  에 대해 변화도를 측정하는 새로운 함수를 만들어 봅시다. #  는 단일 (샘플, 목표 변수) 쌍에 대한 변화도를 계산하는 함수입니다. #  을 사용하면 전체 샘플 및 목표 변수들 배치에 대한 변화도를 알 수 있습니다. # 이때  로 설정했는데, 이는 데이터와 목표 변수의 # 0번째 차원에 대해  를 매핑하고, 매개변수와 버퍼는 # 각 샘플에 대해 똑같이 사용하기 위함입니다. # 마지막으로, 변환됨 함수를 이용해 샘플별 변화도를 계산합니다. #  와  을 사용한 결과가 수동으로 하나씩 처리한 결과와 일치하는지 확인합니다: # 참고:  으로 변환할 수 있는 함수의 유형에는 몇 가지 제한이 있습니다. # 가장 변환하기 좋은 함수는 순수 함수(pure function)입니다. 즉, 출력이 오직 입력에 # 의해서만 결정되고 값 수정과 같은 부작용이 없는 함수입니다. #  은 임의의 파이썬 데이터 구조를 수정하는 작업은 처리할 수 없지만, # 많은 PyTorch 인플레이스(in-place) 연산은 처리할 수 있습니다. # 성능 비교 #  의 성능이 얼마나 차이 나는지 궁금하신가요? # 현재 A100(Ampere)과 같은 최신 GPU에서 가장 좋은 결과를 얻을 수 있고, # 이 예제에서 최대 25배의 속도 향상을 확인했습니다. 한편 다음은 빌드 장비에서의 결과입니다:


# Unmatched

**************************************************
--------- 문제의 코드: 원본에서 백틱 추가를 안해뒀음 ------------ 

원본(https://github.com/PyTorchKorea/tutorials-kr/pull/1059/changes/bbdbcf563b892036c63ce7915bd3897daea0bd90#diff-8d10f0c15a14d63e7f12a6ca4b41ff9f9d83990d495b8ffd1b5f03a66ba774dbL101-L103)
# ``sample_grads[0]`` is the per-sample-grad for model.conv1.weight.
# ``model.conv1.weight.shape`` is ``[32, 1, 3, 3]``; notice how there is one
# gradient, per sample, in the batch for a total of 64.

번역:
# ``sample_grads[0]`` 는 ``model.conv1.weight``에 대한 샘플별 변화도입니다.
# ``model.conv1.weight.shape``는 ``[32, 1, 3, 3]``입니다. 배치 내부에 샘플당 하나씩,
# 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다.

---

그 외 이슈:
expected -> 그래디언트 (번역어: 변화도, json의 synonyms에는 있으나 korean 직접 번역만 따진다.)
expected -> 훈련 (translation guide 에서는 '학습'으로 지정)
expected -> 모델 (원문 문제: model.conv1.wieght로 작성)
expected -> 가중치 (model건과 마찬가지)


**************************************************

file -> intermediate_source/per_sample_grads.py
origin -> gradient
expected -> ['그래디언트']
unmatched
	# In regular model training, one would forward the minibatch through the model, # and then call .backward() to compute gradients.  This would generate an # 'average' gradient of the entire mini-batch: # In contrast to the above approach, per-sample-gradient computation is # equivalent to: # - for each individual sample of the data, perform a forward and a backward #   pass to get an individual (per-sample) gradient.
	# 미니배치를 모델에 주고, .backward()를 호출해서 # 변화도를 계산하는 것이 일반적인 모델 학습 방법입니다. # 곧, 그 미니배치 전체의 '평균적인' 변화도를 생성할 수 있습니다: # 위 방법과는 반대로, 샘플별 변화도 계산은 다음과 같습니다: # - 데이터의 각 샘플에 대해, 순전파와 역전파를 수행하여 #   개별적인(샘플별) 변화도를 구합니다.

file -> intermediate_source/per_sample_grads.py
origin -> training
expected -> ['훈련']
unmatched
	# In regular model training, one would forward the minibatch through the model, # and then call .backward() to compute gradients.  This would generate an # 'average' gradient of the entire mini-batch: # In contrast to the above approach, per-sample-gradient computation is # equivalent to: # - for each individual sample of the data, perform a forward and a backward #   pass to get an individual (per-sample) gradient.
	# 미니배치를 모델에 주고, .backward()를 호출해서 # 변화도를 계산하는 것이 일반적인 모델 학습 방법입니다. # 곧, 그 미니배치 전체의 '평균적인' 변화도를 생성할 수 있습니다: # 위 방법과는 반대로, 샘플별 변화도 계산은 다음과 같습니다: # - 데이터의 각 샘플에 대해, 순전파와 역전파를 수행하여 #   개별적인(샘플별) 변화도를 구합니다.

file -> intermediate_source/per_sample_grads.py
origin -> gradient
expected -> ['그래디언트']
unmatched
	#  is the per-sample-grad for model.conv1.weight. #  is ; notice how there is one # gradient, per sample, in the batch for a total of 64. # Per-sample-grads, *the efficient way*, using function transforms # We can compute per-sample-gradients efficiently by using function transforms. # The  function transform API transforms over functions. # Our strategy is to define a function that computes the loss and then apply # transforms to construct a function that computes per-sample-gradients. # We'll use the  function to treat an  # like a function. # First, let’s extract the state from  into two dictionaries, # parameters and buffers. We'll be detaching them because we won't use # regular PyTorch autograd (e.g. Tensor.backward(), torch.autograd.grad).
	#  는  에 대한 샘플별 변화도입니다. #  는  입니다. 배치 내부에 샘플당 하나씩, # 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다. # 함수 변환(Function Transforms)을 이용한 *효율적인* 샘플별 변화도 계산 # 함수 변환을 사용하면 더 효율적으로 샘플별 변화도를 알 수 있습니다. #  의 함수 변환 API는 함수를 대상으로 동작합니다. # 먼저 손실 함수를 정의하고, 변환해서 # 샘플별 변화도를 계산하는 함수를 형성하는 것이 전략입니다. #  함수를 가지고  을 함수처럼 다룰 것입니다. # 우선,  의 상태를 매개변수와 버퍼, 두 딕셔너리로 추출해야 합니다. # 일반적인 PyTorch autograd(예: Tensor.backward(), torch.autograd.grad)를 # 사용하지 않을 것이기 때문입니다.

file -> intermediate_source/per_sample_grads.py
origin -> weight
expected -> ['가중치', '가중']
unmatched
	#  is the per-sample-grad for model.conv1.weight. #  is ; notice how there is one # gradient, per sample, in the batch for a total of 64. # Per-sample-grads, *the efficient way*, using function transforms # We can compute per-sample-gradients efficiently by using function transforms. # The  function transform API transforms over functions. # Our strategy is to define a function that computes the loss and then apply # transforms to construct a function that computes per-sample-gradients. # We'll use the  function to treat an  # like a function. # First, let’s extract the state from  into two dictionaries, # parameters and buffers. We'll be detaching them because we won't use # regular PyTorch autograd (e.g. Tensor.backward(), torch.autograd.grad).
	#  는  에 대한 샘플별 변화도입니다. #  는  입니다. 배치 내부에 샘플당 하나씩, # 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다. # 함수 변환(Function Transforms)을 이용한 *효율적인* 샘플별 변화도 계산 # 함수 변환을 사용하면 더 효율적으로 샘플별 변화도를 알 수 있습니다. #  의 함수 변환 API는 함수를 대상으로 동작합니다. # 먼저 손실 함수를 정의하고, 변환해서 # 샘플별 변화도를 계산하는 함수를 형성하는 것이 전략입니다. #  함수를 가지고  을 함수처럼 다룰 것입니다. # 우선,  의 상태를 매개변수와 버퍼, 두 딕셔너리로 추출해야 합니다. # 일반적인 PyTorch autograd(예: Tensor.backward(), torch.autograd.grad)를 # 사용하지 않을 것이기 때문입니다.

file -> intermediate_source/per_sample_grads.py
origin -> model
expected -> ['모델', '모형']
unmatched
	#  is the per-sample-grad for model.conv1.weight. #  is ; notice how there is one # gradient, per sample, in the batch for a total of 64. # Per-sample-grads, *the efficient way*, using function transforms # We can compute per-sample-gradients efficiently by using function transforms. # The  function transform API transforms over functions. # Our strategy is to define a function that computes the loss and then apply # transforms to construct a function that computes per-sample-gradients. # We'll use the  function to treat an  # like a function. # First, let’s extract the state from  into two dictionaries, # parameters and buffers. We'll be detaching them because we won't use # regular PyTorch autograd (e.g. Tensor.backward(), torch.autograd.grad).
	#  는  에 대한 샘플별 변화도입니다. #  는  입니다. 배치 내부에 샘플당 하나씩, # 총 64개의 변화도가 있다는 점을 주목하시길 바랍니다. # 함수 변환(Function Transforms)을 이용한 *효율적인* 샘플별 변화도 계산 # 함수 변환을 사용하면 더 효율적으로 샘플별 변화도를 알 수 있습니다. #  의 함수 변환 API는 함수를 대상으로 동작합니다. # 먼저 손실 함수를 정의하고, 변환해서 # 샘플별 변화도를 계산하는 함수를 형성하는 것이 전략입니다. #  함수를 가지고  을 함수처럼 다룰 것입니다. # 우선,  의 상태를 매개변수와 버퍼, 두 딕셔너리로 추출해야 합니다. # 일반적인 PyTorch autograd(예: Tensor.backward(), torch.autograd.grad)를 # 사용하지 않을 것이기 때문입니다.

file -> intermediate_source/per_sample_grads.py
origin -> gradient
expected -> ['그래디언트']
unmatched
	# Now, let’s use the  transform to create a new function that computes # the gradient with respect to the first argument of  # (i.e. the ). # The  function computes the gradient for a single # (sample, target) pair. We can use  to get it to compute the gradient # over an entire batch of samples and targets. Note that #  because we wish to map  over # the 0th dimension of the data and targets, and use the same  and # buffers for each. # Finally, let's used our transformed function to compute per-sample-gradients: # we can double check that the results using  and  match the # results of hand processing each one individually: # A quick note: there are limitations around what types of functions can be # transformed by . The best functions to transform are ones that are pure # functions: a function where the outputs are only determined by the inputs, # and that have no side effects (e.g. mutation).  is unable to handle # mutation of arbitrary Python data structures, but it is able to handle many # in-place PyTorch operations. # Performance comparison # Curious about how the performance of  compares? # Currently the best results are obtained on newer GPU's such as the A100 # (Ampere) where we've seen up to 25x speedups on this example, but here are # some results on our build machines:
	# 이제,  변환을 사용해서  의 첫번째 인자인 # 매개변수  에 대해 변화도를 측정하는 새로운 함수를 만들어 봅시다. #  는 단일 (샘플, 목표 변수) 쌍에 대한 변화도를 계산하는 함수입니다. #  을 사용하면 전체 샘플 및 목표 변수들 배치에 대한 변화도를 알 수 있습니다. # 이때  로 설정했는데, 이는 데이터와 목표 변수의 # 0번째 차원에 대해  를 매핑하고, 매개변수와 버퍼는 # 각 샘플에 대해 똑같이 사용하기 위함입니다. # 마지막으로, 변환됨 함수를 이용해 샘플별 변화도를 계산합니다. #  와  을 사용한 결과가 수동으로 하나씩 처리한 결과와 일치하는지 확인합니다: # 참고:  으로 변환할 수 있는 함수의 유형에는 몇 가지 제한이 있습니다. # 가장 변환하기 좋은 함수는 순수 함수(pure function)입니다. 즉, 출력이 오직 입력에 # 의해서만 결정되고 값 수정과 같은 부작용이 없는 함수입니다. #  은 임의의 파이썬 데이터 구조를 수정하는 작업은 처리할 수 없지만, # 많은 PyTorch 인플레이스(in-place) 연산은 처리할 수 있습니다. # 성능 비교 #  의 성능이 얼마나 차이 나는지 궁금하신가요? # 현재 A100(Ampere)과 같은 최신 GPU에서 가장 좋은 결과를 얻을 수 있고, # 이 예제에서 최대 25배의 속도 향상을 확인했습니다. 한편 다음은 빌드 장비에서의 결과입니다:
