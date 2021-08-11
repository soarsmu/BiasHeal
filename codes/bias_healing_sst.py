from sentiment_analysis import SentimentAnalysis
import pandas as pd
from tqdm import tqdm
import os
import random
import numpy as np
import csv

seed = 42
random.seed(seed)
np.random.seed(seed)


def check_bias(results, alpha):
    '''decide whether it's bias given prediction results of mutants'''
    is_bias = False
    length = len(results)

    if length == 1:
        # no mutants
        pass
    else:
        mid = int((length - 1) / 2)
        male_results = results[1:mid+1]
        female_results = results[mid+1:]

        assert(len(male_results) == len(female_results))

        pos_M = 1.0 * sum(male_results) / len(male_results)
        pos_F = 1.0 * sum(female_results) / len(female_results)
        ### verify property (2) |pos_M - pos_F| < alpha
        is_bias = False if abs(pos_M - pos_F) < alpha else True

    return is_bias

def predict_on_mutants(df, mutant_dir, sa_system, path_to_result):
    '''
    Given `df`, the dataframe containing original test data
    The function goes to `path_to_mutant`, which stores pre-generated mutants
    Then it use `sa_system` to predict sentiments of mutants
    and store results in `path_to_result`
    '''
    with open(path_to_result, mode='w') as f:
        employee_writer = csv.writer(f, delimiter=',')

        #employee_writer.writerow(['John Smith', 'Accounting', 'November'])
        for index, row in tqdm(df.iterrows(), desc="Evaluate"):
            sentiment = row["sentiment"]
            if sentiment >= 0.5:
                label = 1
            else: 
                label = 0
            #label = row["label"]
            text = row["sentence"]
            path_to_mutant = mutant_dir + str(index) + '.csv'
            mutants = [text]
            concrete_templates = []
            if os.path.exists(path_to_mutant):
                # if there are generated mutants
                df_mutant = pd.read_csv(path_to_mutant, names=["label", "mutant", "concrete_template"], sep="\t")
                for index_new, row_new in df_mutant.iterrows():
                    mutants.append(row_new["mutant"])
                    concrete_templates.append(row_new["concrete_template"])
                results = []
                results = sa_system.predict_batch(mutants)
                if len(results) <= 3:
                    continue
                print(len(results))
                #---------
                concrete_templates_result = sa_system.predict(concrete_templates[0])
                

                index_1st_female_mutant = int((len(results)+ 1)/2)
                male_mutants = results[1:index_1st_female_mutant]
                female_mutants = results[index_1st_female_mutant:]

                freq_1_male = sum(male_mutants)
                freq_0_male = len(male_mutants) - freq_1_male
                freq_1_female = sum(female_mutants)
                freq_0_female = len(female_mutants) - freq_1_female
                freq_1_overall = freq_1_male + freq_1_female
                freq_0_overall = freq_0_male + freq_0_female

                if freq_1_male > freq_0_male:
                    results_male_mutants = 1
                else:
                    results_male_mutants = 0
                
                if freq_1_female > freq_0_female:
                    results_female_mutants = 1
                else:
                    results_female_mutants = 0

                if results[0] == 1:
                    freq_1_overall += 1
                else:
                    freq_0_overall += 1
                
                if freq_1_overall > freq_0_overall:
                    results_majority_mutants = 1
                else:
                    results_majority_mutants = 0
                
                results_minority_mutants = 1 - results_majority_mutants

                is_bias = check_bias(results, alpha=0.001)
                employee_writer.writerow([str(index), str(label), str(results[0]), str(results_male_mutants), str(results_female_mutants), str(results_majority_mutants), str(results_minority_mutants), str(concrete_templates_result), str(is_bias)])
                #---------
                #each row: index, label, results_of_original_text, results_of_male_mutants, results_of_female_mutants, results_majority_mutants, results_minority_mutants, concrete_templates_result, is_bias

def analyze_performance(path_to_result):
    '''
    Given `path_to_result`, which stores the file generated by predict_on_mutants(...)
    analyze the accuracy of biased/total predictions.
    '''

    with open(path_to_result, 'r') as f:
        lines = f.readlines()
        total_count = len(lines)
        total_correct_count_original = 0
        majority_count = 0
        minority_count = 0
        male_majority_count = 0
        female_majority_count = 0 
        concrete_template_count = 0
        biased_count = 0
        biased_and_correct_count = 0
        for line in lines:
            true_label = line.split(',')[1]
            pred_label = line.split(',')[2]
            male_majority_label = line.split(',')[3]
            female_majority_label = line.split(',')[4]
            majority_label = line.split(',')[5]
            minority_label = line.split(',')[6]
            concrete_template_label = line.split(',')[7]
            is_bias = line.split(',')[8].strip()

            if true_label == pred_label:
                total_correct_count_original += 1
        
            if is_bias == 'True':
                biased_count += 1
                if true_label == pred_label:
                    biased_and_correct_count += 1
                if true_label == majority_label:
                    majority_count +=1
                if true_label == minority_label:
                    minority_count +=1
                if true_label == male_majority_label:
                    male_majority_count += 1
                if true_label == female_majority_label:
                    female_majority_count += 1
                if true_label == concrete_template_label:
                    concrete_template_count += 1
        
        print("--------USING RESULTS OF ORIGINAL TEXT--------")
        print("Correct Predictions: ", total_correct_count_original)
        print("Total Predictions: ", total_count)
        print("Accuracy: ", 1.0 * total_correct_count_original / total_count)
        print("--------**************--------")
        print("Correct and Biased Predictions: ", biased_and_correct_count)
        print("Total Biased Predictions: ", biased_count)
        print("Accuracy on Biased Predictions: ", 1.0 * biased_and_correct_count / biased_count)

        print("--------USING RESULTS OF MAJORITY MUTANTS--------")
        print("Correct Predictions: ", majority_count)
        print("Total Biased Predictions: ", biased_count)
        print("Accuracy: ", 1.0 * majority_count / biased_count)


        print("--------USING RESULTS OF MINORITY MUTANTS--------")
        print("Correct Predictions: ", minority_count)
        print("Total Biased Predictions: ", biased_count)
        print("Accuracy: ", 1.0 * minority_count / biased_count)

        print("--------USING RESULTS OF MAJORIY OF MALE MUTANTS--------")
        print("Correct Predictions: ", male_majority_count)
        print("Total Biased Predictions: ", biased_count)
        print("Accuracy: ", 1.0 * male_majority_count / biased_count)

        print("--------USING RESULTS OF MAJORITY OF FEMALE MUTANTS--------")
        print("Correct Predictions: ", female_majority_count)
        print("Total Biased Predictions: ", biased_count)
        print("Accuracy: ", 1.0 * female_majority_count / biased_count)

        print("--------USING RESULTS OF CONCRETE TEMPLATE--------")
        print("Correct Predictions: ", concrete_template_count)
        print("Total Biased Predictions: ", biased_count)
        print("Accuracy: ", 1.0 * concrete_template_count / biased_count)


if __name__ == '__main__':

    ## initialize an SA system
    model_checkpoint='./../models/fine-tuning/pytorch_sst_fine_tuned_0.5_split_20_epoch_updated_training_set/epoch20.pt'
    bert_config_file='./../models/uncased_L-12_H-768_A-12/bert_config.json'
    vocab_file='./../models/uncased_L-12_H-768_A-12/vocab.txt'

    sa_system = SentimentAnalysis(model_checkpoint=model_checkpoint,
                                bert_config_file=bert_config_file,
                                vocab_file=vocab_file)
    

    mutant_dir = "../data/biasfinder/gender/sst/mutated_training+0.5_split+20_epoch_fine_tuning+updated_concrete_template_X/each/" 
    # the folder that stores generated mutants.

    #df = pd.read_csv("../asset/imdb/test.csv", names=["label", "sentence"], sep="\t")
    df = pd.read_csv("../asset/sst/test.csv", header = 0, sep=",")
    # original test set

    alpha = 0.001   # specify "tolerance to bias"
    path_to_result = '../result/sst_after_fine_tuning_epoch20_mutable_train+dev+test_0.5_split_+updated_concrete_template+remove_3_mutants_' + str(alpha) + ".csv"

    predict_on_mutants(df, mutant_dir, sa_system, path_to_result)
    # you don't have to call this each time you run

    analyze_performance(path_to_result)
