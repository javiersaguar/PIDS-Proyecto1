import numpy as np

def CalculateCI(num_samples, accuracy):
  """
    Calculate confidence interval for a confidence of 95%
    :param num_samples: Number of samples for the set to evaluate
    :param accuracy: Accuracy of the model
  """
  return 1.96*(np.sqrt(((100-accuracy)*(accuracy))/num_samples))

def find_best_result(model_type, result_list):
    best_index = None
    best_accuracy = -1  # Initialize with a value lower than any possible accuracy

    for index, result in enumerate(result_list):
        if result['model_type'] == model_type and result['accuracy'] > best_accuracy:
            best_index = index
            best_accuracy = result['accuracy']

    return best_index