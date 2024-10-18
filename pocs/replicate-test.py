import replicate
 
output = replicate.run(
  "black-forest-labs/flux-schnell",
  input={"prompt": "an iguana on the beach, pointillism"}
)
print(output)
 
# ['https://replicate.delivery/yhqm/hqSsNRHBbr7qJtsQoEgZ7zPPTfgnxjPU8EIaRfimlT4av7dTA/out-0.jpg']