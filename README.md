# gemtest-webapp

The ``gemtest-webapp`` extends the gemtest framework by a web application that allows you to inspect and analyze your 
gemtest test metamorphic test runs. It features a tabular test report and a metamorphic test case detail view where one 
can examine all artifacts of a single executed metamorphic test case.

First, run a ``gemtest`` test suite with the ``--html-report`` flag:

```console
$ pytest --html-report
```

Then, install ``gemtest-webapp`` via ``pip install gemtest-webapp`` and run it with the path to the gemtest_results folder created by a gemtest pytest run.
Usually, this folder is created in the directory from which pytest was executed.

```console
$ gemtest-webapp --results-dir gemtest_results/
```
## Custom Visualizers

If the input or output of the system under test you are testing is not nicely presentable by a string, one can 
create a visualizer function visualaizing input and output on a static html page. For this, the ``system_under_test`` 
decorator can take functions as optional arguments, such as:

```python
@gmt.system_under_test(
    visualize_input=visualizer.visualize_input,
    visualize_output=visualizer.visualize_output
)
```

The ``visualize_input`` function returns a string that is then embedded in the HTML:

```python
def visualize_input(self, sut_input: Any, **kwargs) -> str:
        mtc = kwargs["mtc"]
        index = kwargs["index"]
        run_id = kwargs["run_id"]
        position = kwargs["position"]

        name = f"{mtc.report.sut_name}." \
               f"{mtc.report.mr_name}." \
               f"{mtc.report.mtc_name}." \
               f"{position}_{index}.png"

        image = (self.transform(sut_input).clone() * 255).view(96, 96)
        plt.clf()
        plt.imshow(image, cmap="gray")
        plt.axis("off")
        return self.savefig(self.image_folder, name, run_id)
```

## Webapp

In the html-report, displayed by the ``gemtest-webapp``, one can see the information of all passed, failed, and skipped 
test cases as well as filter by metamorphic relation, system under test, and test verdict.

![MTC HTML Report](https://raw.githubusercontent.com/tum-i4/gemtest-webapp/main/resources/MTC-html-report.png)


## MTC Detail View

When clicking on the link/name of a specific metamorphic test case, the metamorphic test case detail view opens.
It visualizes the inputs and outputs of the system under test if a custom visualizer is passed.
This makes investigating why one's test case passed or failed faster and more intuitive. 

![MTC Detail View](https://raw.githubusercontent.com/tum-i4/gemtest-webapp/main/resources/MTC-detail-view.png)

## Citation
If you find the ``gemtest`` or ``gemtest-webapp`` framework useful in your research or projects, please consider citing it:

```
@inproceedings{speth2025,
    author = {Speth, Simon and Pretschner, Alexander},
    title = {{GeMTest: A General Metamorphic Testing Framework}},
    booktitle = "Proceedings of the 47th International Conference on Software Engineering, (ICSE-Companion)",
    pages = {1--4},
    address = {Ottawa, ON, Canada},
    year = {2025},
}
```

## License
[MIT License](https://github.com/tum-i4/gemtest-webapp/blob/main/LICENSE)

