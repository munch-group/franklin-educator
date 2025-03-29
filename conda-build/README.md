
# Bacheloruddannelsen Molekylærbiologi og molekylærmedicin

## 1 semester

Introduktion til livets molekyler / Introduction to the Molecules of Life
https://gitlab.au.dk/franklin/introduction-to-the-molecules-of-life

Generel mikrobiologi / General Microbiology
https://gitlab.au.dk/franklin/general-microbiology

Grundlæggende almen kemi / Basic General Chemistry
https://gitlab.au.dk/franklin/basic-general-chemistry

Fysisk biokemi og dataanalyse / Physical Biochemistry and Data Analysis
https://gitlab.au.dk/franklin/physical-biochemistry-and-data-analysis

Human fysiologi i sundhed og sygdom / Human Physiology in Health and Disease
https://gitlab.au.dk/franklin/human-physiology-in-health-and-disease

## 2 semester

Calculus alpha / Calculus alpha
https://gitlab.au.dk/franklin/calculus-alpha

Organisk kemi for molekylærbiologi og molekylær medicin / Organic Chemistry for Molecular Biology and Molecular Medicine
https://gitlab.au.dk/franklin/organic-chemistry-for-molecular-biology-and-molecular-medicine

Molekylær genetik / Molecular Genetics
https://gitlab.au.dk/franklin/molecular-genetics

Molekylærbiologi I: Principper og mekanismer / Molecular Biology I: Principles and Mechanisms
https://gitlab.au.dk/franklin/molecular-biology-i-principles-and-mechanisms

## 3 semester

Bioinformatik / Bioinformatics
https://gitlab.au.dk/franklin/bioinformatics

Strukturbiologi / Structural Biology
https://gitlab.au.dk/franklin/structural-biology

Molekylærbiologi II: Processer, regulering og intervention / Molecular Biology II: Processes, Regulation and Intervention
https://gitlab.au.dk/franklin/molecular-biology-ii-processes-regulation-and-intervention

## 4 semester

Statistical Analysis of Biological and Biomedical Data / Statistical Analysis of Biological and Biomedical Data
https://gitlab.au.dk/franklin/statistical-analysis-of-biological-and-biomedical-data

Metabolisme / Metabolism
https://gitlab.au.dk/franklin/metabolism

Molekylær cellebiologi / Molecular Cell Biology
https://gitlab.au.dk/franklin/molecular-cell-biology

## 5 semester

Anvendt molekylærbiologi og biomedicin / Applied Molecular Biology and Molecular Medicine
https://gitlab.au.dk/franklin/applied-molecular-biology-and-molecular-medicine

Fagets videnskabsteori og etik: Molekylærbiologi og molekylær medicin / Philosophy and Ethics of Science: Molecular Biology and Molecular Medicine
https://gitlab.au.dk/franklin/philosophy-and-ethics-of-science-molecular-biology-and-molecular-medicine


# Kandidatuddannelsen i Bioinformatik


# Kandidatuddannelsen i 



# Build the Conda Package:
    
Navigate to the conda.recipe directory and run:

    conda build .

This command will build the Conda package.

# Install and Test the Package:

After building the package, you can install and test it using:

    conda install -c local my_package

Make sure to replace local with the channel where the package was built.

Remember, this is a simplified example. For more complex packages, you might need to handle additional dependencies, licenses, documentation, and more. It's also important to follow best practices, ensure your package is well-tested, and consider using version control systems like Git to manage your codebase.

# Publish pushed version of conda package

    gh release create --latest "v$(python setup.py --version)" --title "v$(python setup.py --version)" --notes ""
